package de.ownai.app.ui.calendar

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.ownai.app.data.model.CalendarEvent
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.repository.CalendarRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface EventsUiState {
    data object Loading : EventsUiState
    data class Loaded(val events: List<CalendarEvent>) : EventsUiState
    data class Error(val message: String) : EventsUiState
}

class CalendarViewModel(private val calendarRepository: CalendarRepository) : ViewModel() {

    private val _eventsState = MutableStateFlow<EventsUiState>(EventsUiState.Loading)
    val eventsState: StateFlow<EventsUiState> = _eventsState.asStateFlow()

    private val _isSubmitting = MutableStateFlow(false)
    val isSubmitting: StateFlow<Boolean> = _isSubmitting.asStateFlow()

    fun loadEvents(start: String, end: String) {
        viewModelScope.launch {
            _eventsState.value = EventsUiState.Loading
            when (val result = calendarRepository.getEvents(start, end)) {
                is ApiResult.Success ->
                    _eventsState.value = EventsUiState.Loaded(result.data.sortedBy { it.start })

                is ApiResult.Failure -> _eventsState.value = EventsUiState.Error(result.message)
            }
        }
    }

    fun connectCalDav(
        url: String,
        username: String,
        password: String,
        onResult: (success: Boolean, errorMessage: String?) -> Unit
    ) {
        viewModelScope.launch {
            _isSubmitting.value = true
            when (val result = calendarRepository.connectCalDav(url, username, password)) {
                is ApiResult.Success -> onResult(true, null)
                is ApiResult.Failure -> onResult(false, result.message)
            }
            _isSubmitting.value = false
        }
    }

    fun createEvent(
        title: String,
        start: String,
        end: String,
        location: String?,
        onResult: (success: Boolean, errorMessage: String?) -> Unit
    ) {
        viewModelScope.launch {
            _isSubmitting.value = true
            when (val result = calendarRepository.createEvent(title, start, end, location)) {
                is ApiResult.Success -> {
                    onResult(true, null)
                    val current = _eventsState.value
                    if (current is EventsUiState.Loaded) {
                        _eventsState.value =
                            EventsUiState.Loaded((current.events + result.data).sortedBy { it.start })
                    }
                }

                is ApiResult.Failure -> onResult(false, result.message)
            }
            _isSubmitting.value = false
        }
    }
}
