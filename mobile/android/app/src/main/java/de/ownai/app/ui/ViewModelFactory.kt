package de.ownai.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import de.ownai.app.data.AppContainer
import de.ownai.app.ui.auth.AuthViewModel
import de.ownai.app.ui.calendar.CalendarViewModel
import de.ownai.app.ui.chat.ChatViewModel
import de.ownai.app.ui.suggestions.SuggestionsViewModel

/**
 * Small hand-rolled ViewModelProvider.Factory matching [AppContainer]'s
 * manual dependency injection - no Hilt/Dagger for an app this size.
 */
class ViewModelFactory(private val container: AppContainer) : ViewModelProvider.Factory {

    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        return when {
            modelClass.isAssignableFrom(AuthViewModel::class.java) ->
                AuthViewModel(container.authRepository, container.deviceRepository) as T

            modelClass.isAssignableFrom(ChatViewModel::class.java) ->
                ChatViewModel(container.chatRepository) as T

            modelClass.isAssignableFrom(CalendarViewModel::class.java) ->
                CalendarViewModel(container.calendarRepository) as T

            modelClass.isAssignableFrom(SuggestionsViewModel::class.java) ->
                SuggestionsViewModel(container.notificationRepository) as T

            else -> throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
        }
    }
}
