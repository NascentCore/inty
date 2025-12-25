package com.ai.intellimate.settings

import ai.sxwl.android.design.ui.SettingsItemGroup
import ai.sxwl.android.common.ui.ThemeSchemeManager
import ai.sxwl.android.design.theme.IntelliMateThemeScheme
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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
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

private object Spacing {
    val ContentHorizontalPadding = 12.dp
    val SmallSpacer = 4.dp
    val MediumSpacer = 12.dp
    val ChipSpacing = 8.dp
}

private object TextConfig {
    val SecondaryTextAlpha = 0.7f
    val MaxUrlLines = 2
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DebugBackendSettingsEntry(modifier: Modifier = Modifier) {
    val viewModel: DebugBackendSettingsViewModel = viewModel()
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val themeScheme by ThemeSchemeManager.scheme.collectAsStateWithLifecycle()

    SettingsItemGroup {
        Column(modifier = Modifier.fillMaxWidth().padding(Spacing.ContentHorizontalPadding)) {
            Text(
                text = "当前构建类型：${uiState.buildType}",
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
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
            TextButton(onClick = viewModel::resetOverride) {
                Text(text = "恢复默认", color = Color.White)
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
                Text(text = "恢复默认", color = Color.White)
            }

            // UI 主题配色方案（运行时切换）
            Spacer(Modifier.height(Spacing.MediumSpacer * 2))
            Text(
                text = "主题配色方案",
                color = Color.White.copy(alpha = TextConfig.SecondaryTextAlpha),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(Spacing.SmallSpacer))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = if (themeScheme == IntelliMateThemeScheme.Christmas) "圣诞主题" else "默认主题",
                    color = Color.White,
                    fontWeight = FontWeight.Medium,
                )
                Switch(
                    checked = themeScheme == IntelliMateThemeScheme.Christmas,
                    onCheckedChange = { checked ->
                        ThemeSchemeManager.setScheme(
                            if (checked) IntelliMateThemeScheme.Christmas else IntelliMateThemeScheme.Default
                        )
                    },
                )
            }
            Spacer(Modifier.height(Spacing.SmallSpacer))
            TextButton(onClick = ThemeSchemeManager::resetToDefault) {
                Text(text = "恢复默认", color = Color.White)
            }
        }
    }
}
