package de.ownai.app.ui.suggestions

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import de.ownai.app.data.model.Suggestion
import de.ownai.app.ui.ViewModelFactory
import de.ownai.app.ui.common.ErrorBanner
import de.ownai.app.ui.common.LoadingIndicator
import de.ownai.app.ui.common.LogoutAction

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SuggestionsScreen(
    viewModelFactory: ViewModelFactory,
    onLogout: () -> Unit,
    viewModel: SuggestionsViewModel = viewModel(factory = viewModelFactory)
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val pendingIds by viewModel.pendingIds.collectAsStateWithLifecycle()
    val errorMessage by viewModel.errorEvent.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Suggestions") },
                actions = { LogoutAction(onLogout) }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            errorMessage?.let {
                ErrorBanner(message = it)
            }
            Box(modifier = Modifier.fillMaxSize()) {
                when (val state = uiState) {
                    is SuggestionsUiState.Loading -> LoadingIndicator()
                    is SuggestionsUiState.Error -> ErrorBanner(
                        message = state.message,
                        modifier = Modifier.padding(16.dp)
                    )

                    is SuggestionsUiState.Loaded -> {
                        if (state.suggestions.isEmpty()) {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text("No open suggestions right now.")
                            }
                        } else {
                            LazyColumn(
                                modifier = Modifier.fillMaxSize(),
                                contentPadding = PaddingValues(12.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                items(state.suggestions, key = { it.id }) { suggestion ->
                                    SuggestionCard(
                                        suggestion = suggestion,
                                        isPending = pendingIds.contains(suggestion.id),
                                        onApply = { viewModel.apply(suggestion.id) },
                                        onDismiss = { viewModel.dismiss(suggestion.id) }
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SuggestionCard(
    suggestion: Suggestion,
    isPending: Boolean,
    onApply: () -> Unit,
    onDismiss: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                text = suggestionKindLabel(suggestion.kind),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary
            )
            Text(text = suggestion.summary, style = MaterialTheme.typography.bodyLarge)
            Text(
                text = suggestion.created_at,
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            if (isPending) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    CircularProgressIndicator(modifier = Modifier.padding(8.dp), strokeWidth = 2.dp)
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) { Text("Dismiss") }
                    OutlinedButton(onClick = onApply) { Text("Apply") }
                }
            }
        }
    }
}

private fun suggestionKindLabel(kind: String): String = when (kind) {
    "calendar_event" -> "Calendar event detected"
    "reply_draft" -> "Reply suggestion"
    else -> kind
}
