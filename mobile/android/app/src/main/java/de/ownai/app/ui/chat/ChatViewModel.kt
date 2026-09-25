package de.ownai.app.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.ownai.app.data.model.Conversation
import de.ownai.app.data.model.Message
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.repository.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.Instant
import java.util.UUID

sealed interface ChatListUiState {
    data object Loading : ChatListUiState
    data class Loaded(val conversations: List<Conversation>) : ChatListUiState
    data class Error(val message: String) : ChatListUiState
}

/**
 * Backs both the conversation list and a single conversation's thread. Each
 * screen gets its own instance (scoped to its own NavBackStackEntry), so
 * there is no shared-state concern between different open threads.
 */
class ChatViewModel(private val chatRepository: ChatRepository) : ViewModel() {

    private val _listState = MutableStateFlow<ChatListUiState>(ChatListUiState.Loading)
    val listState: StateFlow<ChatListUiState> = _listState.asStateFlow()

    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    private val _isLoadingMessages = MutableStateFlow(false)
    val isLoadingMessages: StateFlow<Boolean> = _isLoadingMessages.asStateFlow()

    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    private val _errorEvent = MutableStateFlow<String?>(null)
    val errorEvent: StateFlow<String?> = _errorEvent.asStateFlow()

    fun loadConversations() {
        viewModelScope.launch {
            _listState.value = ChatListUiState.Loading
            when (val result = chatRepository.getConversations()) {
                is ApiResult.Success ->
                    _listState.value = ChatListUiState.Loaded(result.data.sortedByDescending { it.updated_at })

                is ApiResult.Failure -> _listState.value = ChatListUiState.Error(result.message)
            }
        }
    }

    fun createConversation(onCreated: (conversationId: String) -> Unit) {
        viewModelScope.launch {
            when (val result = chatRepository.createConversation(title = null)) {
                is ApiResult.Success -> onCreated(result.data.id)
                is ApiResult.Failure -> _errorEvent.value = result.message
            }
        }
    }

    fun loadMessages(conversationId: String) {
        viewModelScope.launch {
            _isLoadingMessages.value = true
            when (val result = chatRepository.getMessages(conversationId)) {
                is ApiResult.Success -> _messages.value = result.data
                is ApiResult.Failure -> _errorEvent.value = result.message
            }
            _isLoadingMessages.value = false
        }
    }

    /**
     * POST /chat/conversations/{id}/messages only returns the assistant's
     * reply (API.md), not an echo of what we just sent - so the user's own
     * message is appended locally right away for immediate feedback, and the
     * assistant's reply is appended once the synchronous call returns.
     */
    fun sendMessage(conversationId: String, content: String) {
        val trimmed = content.trim()
        if (trimmed.isEmpty() || _isSending.value) return

        val localUserMessage = Message(
            id = UUID.randomUUID().toString(),
            role = "user",
            content = trimmed,
            tool_calls = null,
            created_at = Instant.now().toString()
        )
        _messages.value = _messages.value + localUserMessage

        viewModelScope.launch {
            _isSending.value = true
            when (val result = chatRepository.sendMessage(conversationId, trimmed)) {
                is ApiResult.Success -> _messages.value = _messages.value + result.data
                is ApiResult.Failure -> _errorEvent.value = result.message
            }
            _isSending.value = false
        }
    }

    fun consumeError() {
        _errorEvent.value = null
    }
}
