package de.ownai.app.data.model

import kotlinx.serialization.Serializable

@Serializable
data class TimersResponse(
    val timers: List<TimerDto>
)

@Serializable
data class TimerDto(
    val id: String,
    val label: String? = null,
    val ends_at: String
)
