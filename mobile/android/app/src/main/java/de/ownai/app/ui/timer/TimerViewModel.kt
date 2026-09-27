package de.ownai.app.ui.timer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.ownai.app.data.model.TimerDto
import de.ownai.app.data.remote.ApiResult
import de.ownai.app.data.repository.TimerRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Fetches active timers once when the main app shell first appears, so a timer set from another
 * device (e.g. via the web app) also gets a local alarm scheduled here - see
 * [de.ownai.app.alarm.TimerAlarmScheduler]. Timers set through this device's own chat get their
 * alarm scheduled directly from the chat screen's tool-call results (no extra round trip
 * needed there) - see [de.ownai.app.alarm.syncTimerAlarmsFromMessages].
 */
class TimerViewModel(private val timerRepository: TimerRepository) : ViewModel() {

    private val _timers = MutableStateFlow<List<TimerDto>>(emptyList())
    val timers: StateFlow<List<TimerDto>> = _timers.asStateFlow()

    fun syncActiveTimers() {
        viewModelScope.launch {
            when (val result = timerRepository.getTimers()) {
                is ApiResult.Success -> _timers.value = result.data
                is ApiResult.Failure -> Unit // best-effort catch-up sync, not worth surfacing an error for
            }
        }
    }
}
