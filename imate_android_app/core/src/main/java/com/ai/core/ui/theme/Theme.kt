package com.ai.core.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

private val lightScheme =
    lightColorScheme(
        primary = primaryLight,
        onPrimary = onPrimaryLight,
        primaryContainer = primaryContainerLight,
        onPrimaryContainer = onPrimaryContainerLight,
        secondary = secondaryLight,
        onSecondary = onSecondaryLight,
        secondaryContainer = secondaryContainerLight,
        onSecondaryContainer = onSecondaryContainerLight,
        tertiary = tertiaryLight,
        onTertiary = onTertiaryLight,
        tertiaryContainer = tertiaryContainerLight,
        onTertiaryContainer = onTertiaryContainerLight,
        error = errorLight,
        onError = onErrorLight,
        errorContainer = errorContainerLight,
        onErrorContainer = onErrorContainerLight,
        background = backgroundLight,
        onBackground = onBackgroundLight,
        surface = surfaceLight,
        onSurface = onSurfaceLight,
        surfaceVariant = surfaceVariantLight,
        onSurfaceVariant = onSurfaceVariantLight,
        outline = outlineLight,
        outlineVariant = outlineVariantLight,
        scrim = scrimLight,
        inverseSurface = inverseSurfaceLight,
        inverseOnSurface = inverseOnSurfaceLight,
        inversePrimary = inversePrimaryLight,
        surfaceDim = surfaceDimLight,
        surfaceBright = surfaceBrightLight,
        surfaceContainerLowest = surfaceContainerLowestLight,
        surfaceContainerLow = surfaceContainerLowLight,
        surfaceContainer = surfaceContainerLight,
        surfaceContainerHigh = surfaceContainerHighLight,
        surfaceContainerHighest = surfaceContainerHighestLight,
    )

data class IntyBrush(
    val gradientBrush1: Brush,
    val gradientBrush2: Brush,
    val gradientBrush3: Brush,
    val gradientBrush4: Brush,
)

data class Brushes(val horizontal: IntyBrush, val vertical: IntyBrush)

private val LightBrushes =
    Brushes(
        horizontal =
            IntyBrush(
                gradientBrush1 = Brush.horizontalGradient(listOf(primaryLight, secondaryLight)),
                gradientBrush2 =
                    Brush.horizontalGradient(
                        listOf(Color(0xFFC3F0FD), Color(0xFF9E97FF), Color(0xFFC567F5))
                    ),
                gradientBrush3 =
                    Brush.horizontalGradient(listOf(Color(0x806E5289), Color(0xFF1C1523))),
                gradientBrush4 =
                    Brush.horizontalGradient(listOf(Color(0xFFFFEECC), Color(0xFFAD9515))),
            ),
        vertical =
            IntyBrush(
                gradientBrush1 = Brush.verticalGradient(listOf(primaryLight, secondaryLight)),
                gradientBrush2 =
                    Brush.verticalGradient(
                        listOf(Color(0xFFC3F0FD), Color(0xFF9E97FF), Color(0xFFC567F5))
                    ),
                gradientBrush3 =
                    Brush.verticalGradient(listOf(Color(0x806E5289), Color(0xFF1C1523))),
                gradientBrush4 =
                    Brush.verticalGradient(listOf(Color(0xFFFFEECC), Color(0xFFAD9515))),
            ),
    )

val MaterialTheme.brushes: Brushes
    get() = LightBrushes

val ColorScheme.textOnLightSurface: Color
    get() = TextOnLightSurface

/** Love Journal 页面配色，供 Heartbeat 等使用 */
val ColorScheme.loveJournalBackground: Color
    get() = LoveJournalColors.background
val ColorScheme.loveJournalBackgroundGradientEnd: Color
    get() = LoveJournalColors.backgroundGradientEnd
val ColorScheme.loveJournalCardBackground: Color
    get() = LoveJournalColors.cardBackground
val ColorScheme.loveJournalOnBackground: Color
    get() = LoveJournalColors.onBackground
val ColorScheme.loveJournalAccent: Color
    get() = LoveJournalColors.accent

@Composable
fun IMateTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = true,
    content: @Composable (() -> Unit),
) {
    val colorScheme = lightScheme
    /*when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> darkScheme
        else -> lightScheme
    }*/
    MaterialTheme(
        colorScheme = colorScheme,
        shapes = Shapes,
        typography = HeartTypography,
        content = content
    )
}
