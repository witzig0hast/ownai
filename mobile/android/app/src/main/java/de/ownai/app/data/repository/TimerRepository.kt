package de.ownai.app.data.repository

import de.ownai.app.data.model.TimerDto
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.safeApiCall
import kotlinx.serialization.json.Json

class TimerRepository(
    private val api: OwnAiApi,
    private val json: Json
) {
    suspend fun getTimers(): ApiResult<List<TimerDto>> =
        safeApiCall(json) { api.getTimers().timers }

    suspend fun cancelTimer(id: String): ApiResult<TimerDto> =
        safeApiCall(json) { api.cancelTimer(id) }
}
