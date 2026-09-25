package de.ownai.app.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.ownai.app.data.AppContainer
import de.ownai.app.data.local.SessionManager
import de.ownai.app.ui.navigation.AuthNavHost
import de.ownai.app.ui.navigation.MainScreen
import de.ownai.app.ui.theme.OwnAiTheme

/** Root composable: gates between the auth flow and the main app based on [SessionManager]. */
@Composable
fun OwnAiApp(container: AppContainer) {
    val viewModelFactory = remember { ViewModelFactory(container) }
    val isLoggedIn by SessionManager.isLoggedIn.collectAsStateWithLifecycle()

    OwnAiTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            if (isLoggedIn) {
                MainScreen(
                    viewModelFactory = viewModelFactory,
                    onLogout = { container.authRepository.logout() }
                )
            } else {
                AuthNavHost(viewModelFactory = viewModelFactory)
            }
        }
    }
}
