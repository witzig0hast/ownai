package de.ownai.app.data.model

import kotlinx.serialization.Serializable

@Serializable
data class VoiceTranscribeResponse(
    val text: String
)
