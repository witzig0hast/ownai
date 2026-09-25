package de.ownai.app.data.model

import kotlinx.serialization.Serializable

/**
 * Every non-2xx response from the OwnAI backend has this exact shape
 * (see API.md, top of file): {"error": {"code": "...", "message": "..."}}
 */
@Serializable
data class ErrorResponse(
    val error: ErrorDetail
)

@Serializable
data class ErrorDetail(
    val code: String,
    val message: String
)
