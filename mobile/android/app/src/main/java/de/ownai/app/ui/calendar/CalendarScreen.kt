package de.ownai.app.ui.calendar

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Link
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import de.ownai.app.data.model.CalendarEvent
import de.ownai.app.ui.ViewModelFactory
import de.ownai.app.ui.common.ErrorBanner
import de.ownai.app.ui.common.LoadingIndicator
import de.ownai.app.ui.common.LogoutAction
import java.time.LocalDate
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalendarScreen(
    viewModelFactory: ViewModelFactory,
    onLogout: () -> Unit,
    viewModel: CalendarViewModel = viewModel(factory = viewModelFactory)
) {
    val eventsState by viewModel.eventsState.collectAsStateWithLifecycle()
    val isSubmitting by viewModel.isSubmitting.collectAsStateWithLifecycle()

    var showConnectDialog by remember { mutableStateOf(false) }
    var showCreateDialog by remember { mutableStateOf(false) }

    // Default window: today through the next 30 days.
    val today = remember { LocalDate.now() }
    val rangeStart = remember(today) { today.format(DateTimeFormatter.ISO_LOCAL_DATE) }
    val rangeEnd = remember(today) { today.plusDays(30).format(DateTimeFormatter.ISO_LOCAL_DATE) }

    LaunchedEffect(rangeStart, rangeEnd) { viewModel.loadEvents(rangeStart, rangeEnd) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Calendar") },
                actions = {
                    IconButton(onClick = { showConnectDialog = true }) {
                        Icon(Icons.Filled.Link, contentDescription = "Connect CalDAV")
                    }
                    IconButton(onClick = { showCreateDialog = true }) {
                        Icon(Icons.Filled.Add, contentDescription = "New event")
                    }
                    LogoutAction(onLogout)
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when (val state = eventsState) {
                is EventsUiState.Loading -> LoadingIndicator()
                is EventsUiState.Error -> ErrorBanner(message = state.message, modifier = Modifier.padding(16.dp))
                is EventsUiState.Loaded -> {
                    if (state.events.isEmpty()) {
                        Box(modifier = Modifier.fillMaxSize()) {
                            Text(
                                text = "No events in the next 30 days.",
                                modifier = Modifier.padding(16.dp)
                            )
                        }
                    } else {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(12.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            items(state.events, key = { it.id }) { event ->
                                EventCard(event)
                            }
                        }
                    }
                }
            }
        }
    }

    if (showConnectDialog) {
        ConnectCalDavDialog(
            isSubmitting = isSubmitting,
            onDismiss = { showConnectDialog = false },
            onSubmit = { url, username, password ->
                viewModel.connectCalDav(url, username, password) { success, _ ->
                    if (success) showConnectDialog = false
                }
            }
        )
    }

    if (showCreateDialog) {
        CreateEventDialog(
            isSubmitting = isSubmitting,
            onDismiss = { showCreateDialog = false },
            onSubmit = { title, start, end, location ->
                viewModel.createEvent(title, start, end, location) { success, _ ->
                    if (success) showCreateDialog = false
                }
            }
        )
    }
}

@Composable
private fun EventCard(event: CalendarEvent) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(text = event.title, style = MaterialTheme.typography.titleLarge)
            Text(text = "${event.start} – ${event.end}", style = MaterialTheme.typography.bodyMedium)
            event.location?.takeIf { it.isNotBlank() }?.let {
                Text(text = it, style = MaterialTheme.typography.bodyMedium)
            }
            Text(
                text = "Source: ${event.source}",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun ConnectCalDavDialog(
    isSubmitting: Boolean,
    onDismiss: () -> Unit,
    onSubmit: (url: String, username: String, password: String) -> Unit
) {
    var url by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Connect CalDAV") },
        text = {
            Column {
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("Server URL") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = username,
                    onValueChange = { username = it },
                    label = { Text("Username") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Password") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onSubmit(url.trim(), username.trim(), password) },
                enabled = !isSubmitting && url.isNotBlank() && username.isNotBlank() && password.isNotBlank()
            ) { Text("Connect") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
private fun CreateEventDialog(
    isSubmitting: Boolean,
    onDismiss: () -> Unit,
    onSubmit: (title: String, start: String, end: String, location: String?) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var start by remember { mutableStateOf("") }
    var end by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("New event") },
        text = {
            Column {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Title") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = start,
                    onValueChange = { start = it },
                    label = { Text("Start (ISO-8601, e.g. 2026-09-25T19:00:00Z)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = end,
                    onValueChange = { end = it },
                    label = { Text("End (ISO-8601)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = location,
                    onValueChange = { location = it },
                    label = { Text("Location (optional)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onSubmit(title.trim(), start.trim(), end.trim(), location.trim().ifBlank { null }) },
                enabled = !isSubmitting && title.isNotBlank() && start.isNotBlank() && end.isNotBlank()
            ) { Text("Create") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}
