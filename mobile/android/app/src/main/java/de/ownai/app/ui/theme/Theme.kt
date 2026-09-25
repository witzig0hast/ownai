package de.ownai.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = OwnAiBlue,
    onPrimary = Color.White,
    primaryContainer = OwnAiBlueContainer,
    secondary = OwnAiSecondary,
    error = OwnAiError,
    background = OwnAiBackgroundLight,
    surface = OwnAiSurfaceLight
)

private val DarkColors = darkColorScheme(
    primary = OwnAiBlueDark,
    onPrimary = Color.Black,
    primaryContainer = OwnAiBlueContainerDark,
    secondary = OwnAiSecondaryDark,
    error = OwnAiErrorDark,
    background = OwnAiBackgroundDark,
    surface = OwnAiSurfaceDark
)

@Composable
fun OwnAiTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColors else LightColors
    MaterialTheme(
        colorScheme = colorScheme,
        typography = OwnAiTypography,
        content = content
    )
}
