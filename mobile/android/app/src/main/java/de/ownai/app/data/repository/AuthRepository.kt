package de.ownai.app.data.repository

import de.ownai.app.data.local.SecurePrefs
import de.ownai.app.data.local.SessionManager
import de.ownai.app.data.model.LoginRequest
import de.ownai.app.data.model.RegisterRequest
import de.ownai.app.data.model.RegisterResponse
import de.ownai.app.data.model.TokenResponse
import de.ownai.app.data.model.UserResponse
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.safeApiCall
import kotlinx.serialization.json.Json

class AuthRepository(
    private val api: OwnAiApi,
    private val securePrefs: SecurePrefs,
    private val json: Json
) {
    suspend fun register(email: String, password: String, displayName: String): ApiResult<RegisterResponse> =
        safeApiCall(json) { api.register(RegisterRequest(email, password, displayName)) }

    /**
     * Stores the token pair on success but deliberately does NOT flip
     * [SessionManager] yet - the caller (see [de.ownai.app.ui.auth.AuthViewModel])
     * still needs to register the device first. Flipping it here would swap
     * the Compose UI over to the main screen immediately, tearing down the
     * AuthViewModel's coroutine scope and cancelling that device-registration
     * call mid-flight.
     */
    suspend fun login(email: String, password: String): ApiResult<TokenResponse> {
        val result = safeApiCall(json) { api.login(LoginRequest(email, password)) }
        if (result is ApiResult.Success) {
            persistTokens(result.data)
        }
        return result
    }

    suspend fun getMe(): ApiResult<UserResponse> = safeApiCall(json) { api.getMe() }

    private fun persistTokens(tokens: TokenResponse) {
        securePrefs.accessToken = tokens.access_token
        securePrefs.refreshToken = tokens.refresh_token
    }

    /**
     * Clears the user's session only. The device API key is kept on purpose
     * (see [SecurePrefs.clearSession]) so notification forwarding keeps
     * working even while logged out of the UI.
     */
    fun logout() {
        securePrefs.clearSession()
        SessionManager.setLoggedIn(false)
    }
}
