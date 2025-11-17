package com.ai.intellimate.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AssistChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.intellimate.ui.components.SettingSection

private object Spacing {
    val SectionTopPadding = 16.dp
    val ContentHorizontalPadding = 12.dp
    val SmallSpacer = 4.dp
    val MediumSpacer = 12.dp
    val ChipSpacing = 8.dp
}

private object TextConfig {
    val SecondaryTextAlpha = 0.7f
    val MaxUrlLines = 2
}

/**
 * Debug-only backend switcher visible in the Settings screen.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DebugBackendSettingsEntry(modifier: Modifier = Modifier) {
    val viewModel: DebugBackendSettingsViewModel = viewModel()
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    SettingSection(modifier = modifier.padding(top = Spacing.SectionTopPadding)) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.ContentHorizontalPadding)) {
            Text(
                text = "当前构建类型：${uiState.buildType}",
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            Text(
                text = "当前生效：${uiState.activeBaseUrl}",
                color = Color.White,
                fontWeight = FontWeight.Medium,
                maxLines = TextConfig.MaxUrlLines,
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.height(Spacing.MediumSpacer))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.ChipSpacing),
                verticalArrangement = Arrangement.spacedBy(Spacing.ChipSpacing)
            ) {
                viewModel.quickPresets.forEach { (label, url) ->
                    AssistChip(
                        onClick = { viewModel.applyPreset(url) },
                        label = { Text(label) }
                    )
                }
            }

            if (uiState.hasOverride) {
                Spacer(Modifier.height(Spacing.MediumSpacer))
                TextButton(onClick = viewModel::resetOverride) {
                    Text(text = "恢复默认", color = Color.White)
                }
            }
        }
    }
}
