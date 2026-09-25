package de.ownai.app.ui.auth

import android.os.Build
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.ownai.app.data.local.SessionManager
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.repository.AuthRepository
import de.ownai.app.data.repository.DeviceRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface AuthUiState {
    data object Idle : AuthUiState
    data object Loading : AuthUiState
    data object Success : AuthUiState
    data class Error(val message: String) : AuthUiState
}

class AuthViewModel(
    private val authRepository: AuthRepository,
    private val deviceRepository: DeviceRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun login(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) {
            _uiState.value = AuthUiState.Error("Please enter your email and password.")
            return
        }
        viewModelScope.launch {
            _uiState.value = AuthUiState.Loading
            when (val result = authRepository.login(email.trim(), password)) {
                is ApiResult.Success -> onLoggedIn()
                is ApiResult.Failure -> _uiState.value = AuthUiState.Error(result.message)
            }
        }
    }

    fun register(email: String, password: String, displayName: String) {
        if (email.isBlank() || password.isBlank() || displayName.isBlank()) {
            _uiState.value = AuthUiState.Error("Please fill in all fields.")
            return
        }
        if (password.length < 8) {
            _uiState.value = AuthUiState.Error("Password must be at least 8 characters.")
            return
        }
        viewModelScope.launch {
            _uiState.value = AuthUiState.Loading
            val registerResult = authRepository.register(email.trim(), password, displayName.trim())
            if (registerResult is ApiResult.Failure) {
                _uiState.value = AuthUiState.Error(registerResult.message)
                return@launch
            }
            // POST /auth/register does not return tokens (API.md) - log in right after
            // so the rest of the first-login flow (device registration) can run.
            when (val loginResult = authRepository.login(email.trim(), password)) {
                is ApiResult.Success -> onLoggedIn()
                is ApiResult.Failure -> _uiState.value = AuthUiState.Error(loginResult.message)
            }
        }
    }

    /**
     * On first successful login, register this phone as a device and store
     * its device_api_key - then, and only then, flip [SessionManager] so the
     * root composable swaps to the main app. Doing it in this order keeps
     * this coroutine (and this ViewModel) alive for the whole device
     * registration call; flipping it earlier would tear this screen (and
     * this viewModelScope) down mid-request.
     */
    private suspend fun onLoggedIn() {
        if (!deviceRepository.isDeviceRegistered()) {
            val label = "${Build.MANUFACTURER} ${Build.MODEL}".trim().ifBlank { "Android device" }
            // Best-effort: login already succeeded, so we don't block the user on this.
            // If it fails, isDeviceRegistered() stays false and this runs again on the next
            // fresh login (see README "known limitations" for a dedicated retry UI).
            deviceRepository.registerDevice(label)
        }
        SessionManager.setLoggedIn(true)
        _uiState.value = AuthUiState.Success
    }

    fun consumeError() {
        if (_uiState.value is AuthUiState.Error) {
            _uiState.value = AuthUiState.Idle
        }
    }
}
