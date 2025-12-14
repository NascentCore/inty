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
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
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
import androidx.compose.ui.tooling.preview.Preview
import ai.sxwl.android.design.theme.IntelliMateTheme
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
        currentCelebration?.let { data -> EnergyCelebrationCard(data = data) }
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

/**
 * 根据总积分值解析应该显示的庆祝级别。
 *
 * 此函数用于判断用户达到特定积分里程碑时是否应该触发庆祝动画。庆祝规则如下：
 * - **首次获得积分**：当 totalPoints == 1 时，返回 First 级别，用于庆祝用户首次获得积分
 * - **十的倍数里程碑**：当积分在 100 以下且是 10 的倍数时（10, 20, 30, ..., 90），返回 Tens 级别
 * - **百的倍数里程碑**：当积分在 1000 以下且是 100 的倍数时（100, 200, 300, ..., 900），返回 Hundreds 级别
 * - **千的倍数里程碑**：当积分达到或超过 1000 且是 1000 的倍数时（1000, 2000, 3000, ...），返回 Thousands 级别
 * - **其他情况**：返回 null，表示不触发庆祝动画
 *
 * 注意：此函数仅判断是否达到里程碑，不检查积分是否增加。调用方需要确保只在积分增加时调用此函数。
 * 对于 0 或负数，此函数会返回 null，不会触发庆祝动画。
 *
 * @param totalPoints 用户当前的总积分值（必须大于 0）
 * @return 对应的庆祝级别，如果不需要庆祝则返回 null
 */
internal fun resolveCelebrationLevel(totalPoints: Int): EnergyCelebrationLevel? {
    if (totalPoints <= 0) return null
    if (totalPoints == 1) return EnergyCelebrationLevel.First
    if (totalPoints < 100 && totalPoints % 10 == 0) return EnergyCelebrationLevel.Tens
    if (totalPoints < 1000 && totalPoints % 100 == 0) return EnergyCelebrationLevel.Hundreds
    if (totalPoints >= 1000 && totalPoints % 1000 == 0) return EnergyCelebrationLevel.Thousands
    return null
}

private data class EnergyCelebrationUiModel(val level: EnergyCelebrationLevel, val totalPoints: Int)

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
    val iconVector =
        when (data.level) {
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

    val primaryText =
        when (data.level) {
            EnergyCelebrationLevel.First -> stringResource(R.string.energy_points_first_title)
            EnergyCelebrationLevel.Tens -> stringResource(R.string.energy_points_tens_title, data.totalPoints)
            EnergyCelebrationLevel.Hundreds ->
                stringResource(R.string.energy_points_hundreds_title, data.totalPoints)
            EnergyCelebrationLevel.Thousands -> stringResource(R.string.energy_points_thousands_title, data.totalPoints)
        }

    val secondaryText =
        when (data.level) {
            EnergyCelebrationLevel.First -> stringResource(R.string.energy_points_first_subtitle)
            EnergyCelebrationLevel.Tens -> stringResource(R.string.energy_points_tens_subtitle)
            EnergyCelebrationLevel.Hundreds ->
                stringResource(R.string.energy_points_hundreds_subtitle)
            EnergyCelebrationLevel.Thousands ->
                stringResource(R.string.energy_points_thousands_subtitle)
        }

    Surface(
        modifier =
            modifier
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
                            fontSize =
                                if (data.level == EnergyCelebrationLevel.First) 18.sp else 16.sp,
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

@Preview(showBackground = true, name = "First Point")
@Composable
private fun EnergyCelebrationCardFirstPreview() {
    IntelliMateTheme {
        EnergyCelebrationCard(
            data = EnergyCelebrationUiModel(
                level = EnergyCelebrationLevel.First,
                totalPoints = 1,
            ),
        )
    }
}

@Preview(showBackground = true, name = "Tens (10 points)")
@Composable
private fun EnergyCelebrationCardTensPreview() {
    IntelliMateTheme {
        EnergyCelebrationCard(
            data = EnergyCelebrationUiModel(
                level = EnergyCelebrationLevel.Tens,
                totalPoints = 10,
            ),
        )
    }
}

@Preview(showBackground = true, name = "Hundreds (100 points)")
@Composable
private fun EnergyCelebrationCardHundredsPreview() {
    IntelliMateTheme {
        EnergyCelebrationCard(
            data = EnergyCelebrationUiModel(
                level = EnergyCelebrationLevel.Hundreds,
                totalPoints = 100,
            ),
        )
    }
}

@Preview(showBackground = true, name = "Thousands (1000 points)")
@Composable
private fun EnergyCelebrationCardThousandsPreview() {
    IntelliMateTheme {
        EnergyCelebrationCard(
            data = EnergyCelebrationUiModel(
                level = EnergyCelebrationLevel.Thousands,
                totalPoints = 1000,
            ),
        )
    }
}
