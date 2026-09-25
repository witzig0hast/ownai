package de.ownai.app.data.local

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * App-wide, in-memory observable login state. Compose navigation collects
 * [isLoggedIn] to decide whether to show the auth flow or the main app.
 *
 * This is intentionally a plain singleton rather than something threaded
 * through DI: it needs to be reachable both from Compose ViewModels and from
 * [de.ownai.app.data.remote.TokenAuthenticator], which runs on an OkHttp
 * background thread with no ViewModel/Compose scope of its own.
 */
object SessionManager {
    private val _isLoggedIn = MutableStateFlow(false)
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()

    fun setLoggedIn(loggedIn: Boolean) {
        _isLoggedIn.value = loggedIn
    }
}
