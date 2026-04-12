package com.ai.intellimate.settings

import ai.sxwl.android.design.ui.SettingsItemGroup
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.intellimate.R

private object Spacing {
    val ContentHorizontalPadding = 12.dp
    val SmallSpacer = 4.dp
    val MediumSpacer = 12.dp
    val ChipSpacing = 8.dp
}

private object TextConfig {
    val SecondaryTextAlpha = 0.7f
    val PlaceholderTextAlpha = 0.5f
    val MaxUrlLines = 2
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DebugBackendSettingsEntry(modifier: Modifier = Modifier) {
    val viewModel: DebugBackendSettingsViewModel = viewModel()
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    SettingsItemGroup {
        Column(modifier = Modifier.fillMaxWidth().padding(Spacing.ContentHorizontalPadding)) {
            Text(
                text = "当前构建类型：${uiState.buildType}",
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            Text(
                text = stringResource(R.string.settings_debug_mode_title),
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text =
                        if (uiState.debugModeEnabled) {
                            stringResource(R.string.settings_debug_mode_on)
                        } else {
                            stringResource(R.string.settings_debug_mode_off)
                        },
                    color = Color.White,
                    fontWeight = FontWeight.Medium,
                )
                Switch(
                    checked = uiState.debugModeEnabled,
                    onCheckedChange = viewModel::setDebugModeEnabled,
                )
            }

            Spacer(Modifier.height(Spacing.MediumSpacer))
            Text(
                text = "当前后端地址：${uiState.activeBaseUrl}",
                color = Color.White,
                fontWeight = FontWeight.Medium,
                maxLines = TextConfig.MaxUrlLines,
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.height(Spacing.MediumSpacer))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.ChipSpacing),
                verticalArrangement = Arrangement.spacedBy(Spacing.ChipSpacing),
            ) {
                viewModel.quickPresets.forEach { (label, url) ->
                    AssistChip(
                        onClick = { viewModel.applySelectedOverride(url) },
                        label = { Text(label) },
                    )
                }
            }

            Spacer(Modifier.height(Spacing.MediumSpacer))
            Text(
                text = stringResource(R.string.settings_debug_custom_backend_label),
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            OutlinedTextField(
                value = uiState.customUrlInput,
                onValueChange = viewModel::setCustomUrlInput,
                modifier = Modifier.fillMaxWidth(),
                placeholder = {
                    Text(
                        stringResource(R.string.settings_debug_custom_backend_placeholder),
                        color = Color.White.copy(alpha = TextConfig.PlaceholderTextAlpha),
                    )
                },
                singleLine = true,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            Button(onClick = viewModel::applyCustomUrl) {
                Text(stringResource(R.string.settings_debug_custom_backend_apply))
            }

            Spacer(Modifier.height(Spacing.MediumSpacer))
            TextButton(onClick = viewModel::resetOverride) {
                Text(
                    text = stringResource(R.string.settings_debug_reset_to_default),
                    color = Color.White,
                )
            }

            // Remix 按钮可见性配置
            Spacer(Modifier.height(Spacing.MediumSpacer * 2))
            Text(
                text = "Remix 按钮可见性",
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = if (uiState.remixButtonVisible) "可见" else "隐藏",
                    color = Color.White,
                    fontWeight = FontWeight.Medium,
                )
                Switch(
                    checked = uiState.remixButtonVisible,
                    onCheckedChange = { viewModel.toggleRemixButton() },
                )
            }
            Spacer(Modifier.height(Spacing.SmallSpacer))
            TextButton(onClick = viewModel::resetRemixButtonOverride) {
                Text(
                    text = stringResource(R.string.settings_debug_reset_to_default),
                    color = Color.White,
                )
            }

            Spacer(Modifier.height(Spacing.MediumSpacer * 2))
            Text(
                text = stringResource(R.string.settings_debug_user_time_context_title),
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text =
                        if (uiState.userTimeContextReportingEnabled) {
                            stringResource(R.string.settings_debug_user_time_context_on)
                        } else {
                            stringResource(R.string.settings_debug_user_time_context_off)
                        },
                    color = Color.White,
                    fontWeight = FontWeight.Medium,
                )
                Switch(
                    checked = uiState.userTimeContextReportingEnabled,
                    onCheckedChange = { viewModel.toggleUserTimeContextReporting() },
                )
            }

        }
    }
}
