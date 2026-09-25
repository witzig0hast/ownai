package de.ownai.app.data.remote

import de.ownai.app.data.local.SecurePrefs
import de.ownai.app.data.local.SessionManager
import de.ownai.app.data.model.RefreshRequest
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

/**
 * Implements the refresh-on-401 flow from API.md: on a 401, calls
 * `POST /auth/refresh` with the stored refresh token, persists the new pair,
 * and retries the original request with the new access token.
 *
 * [refreshApi] must be built with a plain OkHttpClient - no [AuthInterceptor]
 * and no [TokenAuthenticator] attached - otherwise a failing refresh call
 * would recurse back into this authenticator.
 *
 * If the refresh token itself is rejected (401 invalid_refresh_token) or
 * missing, the session is cleared and [SessionManager] flips to logged-out so
 * the UI can navigate back to the login screen.
 */
class TokenAuthenticator(
    private val securePrefs: SecurePrefs,
    private val refreshApi: OwnAiApi
) : Authenticator {

    override fun authenticate(route: Route?, response: Response): Request? {
        val path = response.request.url.encodedPath
        // Never try to "refresh" a failed auth call or a device-key ingest call.
        if (path.contains("/auth/") || path.endsWith("/notifications/ingest")) {
            return null
        }

        // Avoid infinite retry loops if the freshly-refreshed token also gets a 401.
        if (responseCount(response) >= 2) {
            return null
        }

        val failedAccessToken = response.request.header("Authorization")?.removePrefix("Bearer ")

        synchronized(this) {
            val currentAccessToken = securePrefs.accessToken
            // Another request already refreshed while we were waiting on the lock.
            if (currentAccessToken != null && currentAccessToken != failedAccessToken) {
                return response.request.newBuilder()
                    .header("Authorization", "Bearer $currentAccessToken")
                    .build()
            }

            val refreshToken = securePrefs.refreshToken
            if (refreshToken == null) {
                securePrefs.clearSession()
                SessionManager.setLoggedIn(false)
                return null
            }

            return try {
                val tokens = runBlocking { refreshApi.refresh(RefreshRequest(refreshToken)) }
                securePrefs.accessToken = tokens.access_token
                securePrefs.refreshToken = tokens.refresh_token
                response.request.newBuilder()
                    .header("Authorization", "Bearer ${tokens.access_token}")
                    .build()
            } catch (e: Exception) {
                // invalid_refresh_token or network failure during refresh: force logout.
                securePrefs.clearSession()
                SessionManager.setLoggedIn(false)
                null
            }
        }
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) {
            count++
            prior = prior.priorResponse
        }
        return count
    }
}
