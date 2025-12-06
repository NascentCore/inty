/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.chat.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import kotlinx.coroutines.delay

@Composable
fun EnergyCelebrationBanner(
    totalPoints: Int,
    enabled: Boolean,
    modifier: Modifier = Modifier,
    autoDismissMillis: Long = 2800,
) {
    var lastObservedPoints by remember { mutableIntStateOf(totalPoints) }
    var celebration by remember { mutableStateOf<EnergyCelebrationUiModel?>(null) }

    LaunchedEffect(totalPoints, enabled) {
        if (!enabled) {
            lastObservedPoints = totalPoints
            celebration = null
            return@LaunchedEffect
        }
        if (totalPoints <= 0) {
            lastObservedPoints = totalPoints
            return@LaunchedEffect
        }
        if (totalPoints <= lastObservedPoints) {
            lastObservedPoints = totalPoints
            return@LaunchedEffect
        }
        resolveCelebrationLevel(totalPoints)?.let { level ->
            celebration = EnergyCelebrationUiModel(level, totalPoints)
        }
        lastObservedPoints = totalPoints
    }

    val currentCelebration = celebration

    AnimatedVisibility(
        visible = currentCelebration != null && enabled,
        enter = fadeIn() + slideInVertically { -it },
        exit = slideOutVertically { -it } + fadeOut(),
        modifier = modifier,
    ) {
        currentCelebration?.let { data ->
            EnergyCelebrationCard(data = data)
        }
    }

    LaunchedEffect(currentCelebration, enabled) {
        if (!enabled) {
            celebration = null
            return@LaunchedEffect
        }
        if (currentCelebration != null) {
            delay(autoDismissMillis)
            celebration = null
        }
    }
}

private fun resolveCelebrationLevel(totalPoints: Int): EnergyCelebrationLevel? {
    if (totalPoints == 1) return EnergyCelebrationLevel.First
    if (totalPoints % 1000 == 0) return EnergyCelebrationLevel.Thousands
    if (totalPoints % 100 == 0) return EnergyCelebrationLevel.Hundreds
    if (totalPoints % 10 == 0) return EnergyCelebrationLevel.Tens
    return null
}

private data class EnergyCelebrationUiModel(
    val level: EnergyCelebrationLevel,
    val totalPoints: Int,
)

enum class EnergyCelebrationLevel {
    First,
    Tens,
    Hundreds,
    Thousands,
}

@Composable
private fun EnergyCelebrationCard(data: EnergyCelebrationUiModel, modifier: Modifier = Modifier) {
    val backgroundColor: Color
    val iconTint: Color
    val textColor: Color
    val subtitleColor: Color
    val iconVector = when (data.level) {
        EnergyCelebrationLevel.First -> Icons.Rounded.AutoAwesome
        else -> Icons.Rounded.EmojiEvents
    }

    when (data.level) {
        EnergyCelebrationLevel.First -> {
            backgroundColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.95f)
            iconTint = MaterialTheme.colorScheme.primary
            textColor = MaterialTheme.colorScheme.onSurface
            subtitleColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
        }
        EnergyCelebrationLevel.Tens -> {
            backgroundColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.95f)
            iconTint = MaterialTheme.colorScheme.onPrimaryContainer
            textColor = MaterialTheme.colorScheme.onPrimaryContainer
            subtitleColor = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.9f)
        }
        EnergyCelebrationLevel.Hundreds -> {
            backgroundColor = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.95f)
            iconTint = MaterialTheme.colorScheme.onSecondaryContainer
            textColor = MaterialTheme.colorScheme.onSecondaryContainer
            subtitleColor = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.9f)
        }
        EnergyCelebrationLevel.Thousands -> {
            backgroundColor = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.95f)
            iconTint = MaterialTheme.colorScheme.onTertiaryContainer
            textColor = MaterialTheme.colorScheme.onTertiaryContainer
            subtitleColor = MaterialTheme.colorScheme.onTertiaryContainer.copy(alpha = 0.9f)
        }
    }

    val primaryText = when (data.level) {
        EnergyCelebrationLevel.First ->
            stringResource(R.string.energy_points_first_title)
        else ->
            stringResource(
                R.string.energy_points_tens_title,
                data.totalPoints,
            )
    }

    val secondaryText = when (data.level) {
        EnergyCelebrationLevel.First ->
            stringResource(R.string.energy_points_first_subtitle)
        EnergyCelebrationLevel.Tens ->
            stringResource(R.string.energy_points_tens_subtitle)
        EnergyCelebrationLevel.Hundreds ->
            stringResource(R.string.energy_points_hundreds_subtitle)
        EnergyCelebrationLevel.Thousands ->
            stringResource(R.string.energy_points_thousands_subtitle)
    }

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .widthIn(max = 420.dp)
            .shadow(elevation = 8.dp, shape = RoundedCornerShape(28.dp)),
        shape = RoundedCornerShape(28.dp),
        color = backgroundColor,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = iconVector,
                contentDescription = null,
                tint = iconTint,
                modifier = Modifier.size(36.dp),
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = primaryText,
                    color = textColor,
                    style =
                        MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.Bold,
                            fontSize = if (data.level == EnergyCelebrationLevel.First) 18.sp else 16.sp,
                        ),
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = secondaryText,
                    color = subtitleColor,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}
