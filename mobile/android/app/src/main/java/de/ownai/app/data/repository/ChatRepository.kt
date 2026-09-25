package de.ownai.app.data.repository

import de.ownai.app.data.model.Conversation
import de.ownai.app.data.model.CreateConversationRequest
import de.ownai.app.data.model.Message
import de.ownai.app.data.model.SendMessageRequest
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.safeApiCall
import kotlinx.serialization.json.Json

class ChatRepository(
    private val api: OwnAiApi,
    private val json: Json
) {
    suspend fun getConversations(): ApiResult<List<Conversation>> =
        safeApiCall(json) { api.getConversations().conversations }

    suspend fun createConversation(title: String?): ApiResult<Conversation> =
        safeApiCall(json) { api.createConversation(CreateConversationRequest(title)) }

    suspend fun getMessages(conversationId: String): ApiResult<List<Message>> =
        safeApiCall(json) { api.getMessages(conversationId).messages }

    /** Synchronous per API.md: suspends until the assistant's full reply (incl. tool calls) is ready. */
    suspend fun sendMessage(conversationId: String, content: String): ApiResult<Message> =
        safeApiCall(json) { api.sendMessage(conversationId, SendMessageRequest(content)).message }
}
