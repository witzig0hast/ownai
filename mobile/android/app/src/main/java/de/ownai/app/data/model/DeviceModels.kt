package de.ownai.app.data.model

import kotlinx.serialization.Serializable

@Serializable
data class DeviceRegisterRequest(
    val platform: String,
    val push_token: String? = null,
    val label: String
)

@Serializable
data class DeviceRegisterResponse(
    val id: String,
    val platform: String,
    /**
     * Only ever returned by this call. It is persisted immediately by
     * DeviceRepository into EncryptedSharedPreferences - if it is lost the
     * user has to re-register the device to get a new one.
     */
    val device_api_key: String,
    val label: String
)
