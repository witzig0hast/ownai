package de.ownai.app.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Encrypted, on-device storage for everything that must never leak in plain
 * text: the JWT access/refresh token pair and the per-device API key used by
 * the notification listener (see API.md, "Geräte" section).
 *
 * Backed by Jetpack Security's EncryptedSharedPreferences, which wraps a
 * regular SharedPreferences file with AES-256-GCM (values) / AES-256-SIV
 * (keys), with the master key itself held in the Android Keystore.
 */
class SecurePrefs(context: Context) {

    private val appContext = context.applicationContext

    private val masterKey: MasterKey by lazy {
        MasterKey.Builder(appContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
    }

    private val prefs: SharedPreferences by lazy {
        EncryptedSharedPreferences.create(
            appContext,
            PREFS_FILE_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    var accessToken: String?
        get() = prefs.getString(KEY_ACCESS_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_ACCESS_TOKEN, value).apply()

    var refreshToken: String?
        get() = prefs.getString(KEY_REFRESH_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_REFRESH_TOKEN, value).apply()

    /** device_api_key from POST /devices/register - retrievable only once from the API. */
    var deviceApiKey: String?
        get() = prefs.getString(KEY_DEVICE_API_KEY, null)
        set(value) = prefs.edit().putString(KEY_DEVICE_API_KEY, value).apply()

    fun hasSession(): Boolean = accessToken != null && refreshToken != null

    fun hasDeviceKey(): Boolean = deviceApiKey != null

    /** Called on logout. Deliberately keeps the device API key: the device
     * stays registered with the backend, and notification forwarding keeps
     * working (by design, decoupled from the user's login session - see
     * API.md) even while nobody is logged into the UI. */
    fun clearSession() {
        prefs.edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .apply()
    }

    private companion object {
        const val PREFS_FILE_NAME = "ownai_secure_prefs"
        const val KEY_ACCESS_TOKEN = "access_token"
        const val KEY_REFRESH_TOKEN = "refresh_token"
        const val KEY_DEVICE_API_KEY = "device_api_key"
    }
}
