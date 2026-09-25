package de.ownai.app.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import de.ownai.app.ui.ViewModelFactory
import de.ownai.app.ui.calendar.CalendarScreen
import de.ownai.app.ui.chat.ChatThreadScreen
import de.ownai.app.ui.chat.ConversationListScreen
import de.ownai.app.ui.notifications.NotificationAccessScreen
import de.ownai.app.ui.suggestions.SuggestionsScreen

private data class BottomNavItem(val route: String, val label: String, val icon: ImageVector)

private val bottomNavItems = listOf(
    BottomNavItem(MainRoutes.CHAT_LIST, "Chat", Icons.Filled.Chat),
    BottomNavItem(MainRoutes.CALENDAR, "Calendar", Icons.Filled.CalendarMonth),
    BottomNavItem(MainRoutes.SUGGESTIONS, "Suggestions", Icons.Filled.Lightbulb),
    BottomNavItem(MainRoutes.NOTIFICATION_ACCESS, "Notifications", Icons.Filled.NotificationsActive)
)

/** Everything behind the bottom navigation bar - shown once [de.ownai.app.data.local.SessionManager] is logged in. */
@Composable
fun MainScreen(viewModelFactory: ViewModelFactory, onLogout: () -> Unit) {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            val backStackEntry by navController.currentBackStackEntryAsState()
            val currentRoute = backStackEntry?.destination?.route

            NavigationBar {
                bottomNavItems.forEach { item ->
                    NavigationBarItem(
                        selected = currentRoute == item.route,
                        onClick = {
                            navController.navigate(item.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(item.icon, contentDescription = item.label) },
                        label = { Text(item.label) }
                    )
                }
            }
        }
    ) { outerPadding ->
        NavHost(
            navController = navController,
            startDestination = MainRoutes.CHAT_LIST,
            modifier = Modifier.padding(outerPadding)
        ) {
            composable(MainRoutes.CHAT_LIST) {
                ConversationListScreen(
                    viewModelFactory = viewModelFactory,
                    onOpenConversation = { conversationId ->
                        navController.navigate(MainRoutes.chatThread(conversationId))
                    },
                    onLogout = onLogout
                )
            }
            composable(
                route = MainRoutes.CHAT_THREAD,
                arguments = listOf(navArgument(MainRoutes.CHAT_THREAD_ARG) { type = NavType.StringType })
            ) { backStackEntry ->
                val conversationId = backStackEntry.arguments?.getString(MainRoutes.CHAT_THREAD_ARG)
                if (conversationId != null) {
                    ChatThreadScreen(
                        conversationId = conversationId,
                        viewModelFactory = viewModelFactory,
                        onBack = { navController.popBackStack() }
                    )
                }
            }
            composable(MainRoutes.CALENDAR) {
                CalendarScreen(viewModelFactory = viewModelFactory, onLogout = onLogout)
            }
            composable(MainRoutes.SUGGESTIONS) {
                SuggestionsScreen(viewModelFactory = viewModelFactory, onLogout = onLogout)
            }
            composable(MainRoutes.NOTIFICATION_ACCESS) {
                NotificationAccessScreen(onLogout = onLogout)
            }
        }
    }
}
