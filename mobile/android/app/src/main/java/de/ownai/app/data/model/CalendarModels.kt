package de.ownai.app.data.model

import kotlinx.serialization.Serializable

@Serializable
data class ConnectCalDavRequest(
    val url: String,
    val username: String,
    val password: String
)

@Serializable
data class ConnectCalDavResponse(
    val connected: Boolean
)

@Serializable
data class EventsResponse(
    val events: List<CalendarEvent>
)

@Serializable
data class CalendarEvent(
    val id: String,
    val title: String,
    val start: String,
    val end: String,
    val location: String? = null,
    val source: String
)

@Serializable
data class CreateEventRequest(
    val title: String,
    val start: String,
    val end: String,
    val location: String? = null
)
