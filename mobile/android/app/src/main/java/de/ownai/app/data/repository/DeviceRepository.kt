package de.ownai.app.data.repository

import de.ownai.app.data.local.SecurePrefs
import de.ownai.app.data.model.DeviceRegisterRequest
import de.ownai.app.data.model.DeviceRegisterResponse
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.safeApiCall
import kotlinx.serialization.json.Json

class DeviceRepository(
    private val api: OwnAiApi,
    private val securePrefs: SecurePrefs,
    private val json: Json
) {
    fun isDeviceRegistered(): Boolean = securePrefs.hasDeviceKey()

    /**
     * Registers this phone as an Android device on the backend and persists
     * the returned device_api_key immediately - it is returned by the API
     * exactly once (see API.md, "Geräte") and cannot be fetched again.
     */
    suspend fun registerDevice(label: String): ApiResult<DeviceRegisterResponse> {
        val result = safeApiCall(json) {
            api.registerDevice(DeviceRegisterRequest(platform = "android", push_token = null, label = label))
        }
        if (result is ApiResult.Success) {
            securePrefs.deviceApiKey = result.data.device_api_key
        }
        return result
    }
}
