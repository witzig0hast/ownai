package de.ownai.app.data.repository

import de.ownai.app.data.model.CalendarEvent
import de.ownai.app.data.model.ConnectCalDavRequest
import de.ownai.app.data.model.CreateEventRequest
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.safeApiCall
import kotlinx.serialization.json.Json

class CalendarRepository(
    private val api: OwnAiApi,
    private val json: Json
) {
    suspend fun connectCalDav(url: String, username: String, password: String): ApiResult<Boolean> =
        safeApiCall(json) { api.connectCalDav(ConnectCalDavRequest(url, username, password)).connected }

    suspend fun getEvents(start: String, end: String): ApiResult<List<CalendarEvent>> =
        safeApiCall(json) { api.getEvents(start, end).events }

    suspend fun createEvent(
        title: String,
        start: String,
        end: String,
        location: String?
    ): ApiResult<CalendarEvent> =
        safeApiCall(json) { api.createEvent(CreateEventRequest(title, start, end, location)) }
}
