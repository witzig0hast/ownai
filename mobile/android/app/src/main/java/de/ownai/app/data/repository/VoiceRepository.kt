package de.ownai.app.data.repository

import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.safeApiCall
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class VoiceRepository(
    private val api: OwnAiApi,
    private val json: Json
) {
    suspend fun transcribe(audioFile: File, mimeType: String): ApiResult<String> {
        val requestBody = audioFile.asRequestBody(mimeType.toMediaType())
        val part = MultipartBody.Part.createFormData("audio", audioFile.name, requestBody)
        return safeApiCall(json) { api.transcribeVoice(part).text }
    }
}
