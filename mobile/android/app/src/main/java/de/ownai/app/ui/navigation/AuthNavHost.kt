package de.ownai.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import de.ownai.app.ui.ViewModelFactory
import de.ownai.app.ui.auth.LoginScreen
import de.ownai.app.ui.auth.RegisterScreen

/** Shown while [de.ownai.app.data.local.SessionManager] is logged out. */
@Composable
fun AuthNavHost(viewModelFactory: ViewModelFactory) {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = AuthRoutes.LOGIN) {
        composable(AuthRoutes.LOGIN) {
            LoginScreen(
                viewModelFactory = viewModelFactory,
                onNavigateToRegister = { navController.navigate(AuthRoutes.REGISTER) }
            )
        }
        composable(AuthRoutes.REGISTER) {
            RegisterScreen(
                viewModelFactory = viewModelFactory,
                onNavigateToLogin = { navController.popBackStack() }
            )
        }
    }
}
