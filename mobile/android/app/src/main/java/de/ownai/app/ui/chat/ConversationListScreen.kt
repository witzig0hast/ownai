package de.ownai.app.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import de.ownai.app.data.model.Conversation
import de.ownai.app.ui.ViewModelFactory
import de.ownai.app.ui.common.ErrorBanner
import de.ownai.app.ui.common.LoadingIndicator
import de.ownai.app.ui.common.LogoutAction

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConversationListScreen(
    viewModelFactory: ViewModelFactory,
    onOpenConversation: (String) -> Unit,
    onLogout: () -> Unit,
    viewModel: ChatViewModel = viewModel(factory = viewModelFactory)
) {
    val listState by viewModel.listState.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadConversations() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Chat") },
                actions = { LogoutAction(onLogout) }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = {
                viewModel.createConversation(onCreated = onOpenConversation)
            }) {
                Icon(Icons.Filled.Add, contentDescription = "New conversation")
            }
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when (val state = listState) {
                is ChatListUiState.Loading -> LoadingIndicator()
                is ChatListUiState.Error -> ErrorBanner(
                    message = state.message,
                    modifier = Modifier.padding(16.dp)
                )

                is ChatListUiState.Loaded -> {
                    if (state.conversations.isEmpty()) {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Text("No conversations yet. Tap + to start one.")
                        }
                    } else {
                        LazyColumn(modifier = Modifier.fillMaxSize()) {
                            items(state.conversations, key = { it.id }) { conversation ->
                                ConversationRow(
                                    conversation = conversation,
                                    onClick = { onOpenConversation(conversation.id) }
                                )
                                HorizontalDivider()
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ConversationRow(conversation: Conversation, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .background(MaterialTheme.colorScheme.surface)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        Text(
            text = conversation.title?.takeIf { it.isNotBlank() } ?: "Untitled conversation",
            style = MaterialTheme.typography.bodyLarge
        )
        Text(
            text = conversation.updated_at,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
