package de.ownai.app.data.repository

import de.ownai.app.data.local.SecurePrefs
import de.ownai.app.data.model.IngestRequest
import de.ownai.app.data.model.IngestResponse
import de.ownai.app.data.model.Suggestion
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.safeApiCall
import kotlinx.serialization.json.Json

class NotificationRepository(
    private val api: OwnAiApi,
    private val securePrefs: SecurePrefs,
    private val json: Json
) {
    /**
     * Forwards one captured notification to the backend, authenticated with
     * the per-device API key (never the user's JWT - see API.md). Called from
     * [de.ownai.app.notification.NotificationForwardingService].
     */
    suspend fun ingest(request: IngestRequest): ApiResult<IngestResponse> {
        val deviceApiKey = securePrefs.deviceApiKey
            ?: return ApiResult.Failure(code = null, message = "Device is not registered yet")
        return safeApiCall(json) { api.ingestNotification(deviceApiKey, request) }
    }

    suspend fun getOpenSuggestions(): ApiResult<List<Suggestion>> =
        safeApiCall(json) { api.getSuggestions(status = "open").suggestions }

    suspend fun applySuggestion(id: String): ApiResult<Suggestion> =
        safeApiCall(json) { api.applySuggestion(id) }

    suspend fun dismissSuggestion(id: String): ApiResult<String> =
        safeApiCall(json) { api.dismissSuggestion(id).status }
}
