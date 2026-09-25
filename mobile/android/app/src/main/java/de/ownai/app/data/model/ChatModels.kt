package de.ownai.app.data.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class ConversationsResponse(
    val conversations: List<Conversation>
)

@Serializable
data class Conversation(
    val id: String,
    val title: String? = null,
    val updated_at: String
)

@Serializable
data class CreateConversationRequest(
    val title: String? = null
)

@Serializable
data class MessagesResponse(
    val messages: List<Message>
)

@Serializable
data class Message(
    val id: String,
    val role: String, // "user" | "assistant" | "tool"
    val content: String,
    val tool_calls: List<ToolCall>? = null,
    val created_at: String
)

@Serializable
data class ToolCall(
    val tool: String,
    val arguments: JsonElement? = null,
    val result: JsonElement? = null
)

@Serializable
data class SendMessageRequest(
    val content: String
)

@Serializable
data class SendMessageResponse(
    val message: Message
)
