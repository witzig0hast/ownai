package de.ownai.app.data.remote

import de.ownai.app.data.model.ErrorResponse
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException

/** UI-friendly outcome of an API call - repositories never let Retrofit exceptions escape. */
sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Failure(val code: String?, val message: String) : ApiResult<Nothing>()
}

/**
 * Runs [block] (a suspend Retrofit call) and turns any failure into
 * [ApiResult.Failure], parsing the {"error": {"code", "message"}} body from
 * API.md when one is present.
 */
suspend fun <T> safeApiCall(json: Json, block: suspend () -> T): ApiResult<T> {
    return try {
        ApiResult.Success(block())
    } catch (e: HttpException) {
        val parsed = parseErrorBody(json, e)
        ApiResult.Failure(
            code = parsed?.error?.code,
            message = parsed?.error?.message ?: "Server error (HTTP ${e.code()})"
        )
    } catch (e: IOException) {
        ApiResult.Failure(code = null, message = "Network error: ${e.message ?: "no connection"}")
    } catch (e: SerializationException) {
        ApiResult.Failure(code = null, message = "Unexpected server response")
    }
}

private fun parseErrorBody(json: Json, e: HttpException): ErrorResponse? {
    return try {
        val body = e.response()?.errorBody()?.string() ?: return null
        json.decodeFromString(ErrorResponse.serializer(), body)
    } catch (ex: Exception) {
        // Reading/parsing the error body is best-effort only - fall back to a generic
        // message (built from e.code() by the caller) rather than let this throw.
        null
    }
}
