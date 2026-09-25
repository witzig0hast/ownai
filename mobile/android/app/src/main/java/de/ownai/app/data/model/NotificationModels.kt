package de.ownai.app.data.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class IngestRequest(
    val package_name: String,
    val app_label: String,
    val title: String,
    val text: String,
    val posted_at: String,
    val category: String // "msg" | "sms" | "other"
)

@Serializable
data class IngestResponse(
    val accepted: Boolean,
    val notification_id: String
)

@Serializable
data class SuggestionsResponse(
    val suggestions: List<Suggestion>
)

@Serializable
data class Suggestion(
    val id: String,
    val notification_id: String,
    val kind: String, // "calendar_event" | "reply_draft"
    val summary: String,
    val payload: JsonElement? = null,
    val status: String, // "open" | "applied" | "dismissed"
    val created_at: String
)

@Serializable
data class DismissResponse(
    val status: String
)
