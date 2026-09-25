package de.ownai.app.ui.suggestions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.ownai.app.data.model.Suggestion
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.repository.NotificationRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface SuggestionsUiState {
    data object Loading : SuggestionsUiState
    data class Loaded(val suggestions: List<Suggestion>) : SuggestionsUiState
    data class Error(val message: String) : SuggestionsUiState
}

class SuggestionsViewModel(private val notificationRepository: NotificationRepository) : ViewModel() {

    private val _uiState = MutableStateFlow<SuggestionsUiState>(SuggestionsUiState.Loading)
    val uiState: StateFlow<SuggestionsUiState> = _uiState.asStateFlow()

    /** IDs currently being applied/dismissed, so their row can show a spinner and disable its buttons. */
    private val _pendingIds = MutableStateFlow<Set<String>>(emptySet())
    val pendingIds: StateFlow<Set<String>> = _pendingIds.asStateFlow()

    private val _errorEvent = MutableStateFlow<String?>(null)
    val errorEvent: StateFlow<String?> = _errorEvent.asStateFlow()

    fun load() {
        viewModelScope.launch {
            _uiState.value = SuggestionsUiState.Loading
            when (val result = notificationRepository.getOpenSuggestions()) {
                is ApiResult.Success -> _uiState.value = SuggestionsUiState.Loaded(result.data)
                is ApiResult.Failure -> _uiState.value = SuggestionsUiState.Error(result.message)
            }
        }
    }

    fun apply(suggestionId: String) {
        runPendingAction(suggestionId) { notificationRepository.applySuggestion(suggestionId) }
    }

    fun dismiss(suggestionId: String) {
        runPendingAction(suggestionId) { notificationRepository.dismissSuggestion(suggestionId) }
    }

    private fun runPendingAction(suggestionId: String, action: suspend () -> ApiResult<*>) {
        viewModelScope.launch {
            _pendingIds.value = _pendingIds.value + suggestionId
            when (val result = action()) {
                is ApiResult.Success -> removeFromList(suggestionId)
                is ApiResult.Failure -> _errorEvent.value = result.message
            }
            _pendingIds.value = _pendingIds.value - suggestionId
        }
    }

    private fun removeFromList(suggestionId: String) {
        val current = _uiState.value
        if (current is SuggestionsUiState.Loaded) {
            _uiState.value = SuggestionsUiState.Loaded(current.suggestions.filterNot { it.id == suggestionId })
        }
    }

    fun consumeError() {
        _errorEvent.value = null
    }
}
