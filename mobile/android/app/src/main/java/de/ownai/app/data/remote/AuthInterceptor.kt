package de.ownai.app.data.remote

import de.ownai.app.data.local.SecurePrefs
import okhttp3.Interceptor
import okhttp3.Response

/**
 * Attaches "Authorization: Bearer <access_token>" to every request, except
 * `/auth/*` (no session yet) and `/notifications/ingest` (uses its own
 * X-Device-Key header instead - see API.md, "Geräte").
 */
class AuthInterceptor(private val securePrefs: SecurePrefs) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val path = original.url.encodedPath

        if (path.contains("/auth/") || path.endsWith("/notifications/ingest")) {
            return chain.proceed(original)
        }

        val accessToken = securePrefs.accessToken
            ?: return chain.proceed(original)

        val authorized = original.newBuilder()
            .header("Authorization", "Bearer $accessToken")
            .build()
        return chain.proceed(authorized)
    }
}
