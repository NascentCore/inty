package com.ai.intellimate.settings

import android.text.format.DateFormat
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
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.ui.components.SettingSection

/**
 * Debug-only backend switcher visible in the Settings screen.
 *
 * The UI is rendered only when running the `debug` build type.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DebugBackendSettingsEntry(modifier: Modifier = Modifier) {
    if (!BuildConfig.BUILD_TYPE.equals("debug", ignoreCase = true)) return

    val viewModel: DebugBackendSettingsViewModel = viewModel()
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    if (!uiState.isSupported) return

    val lastUpdatedText =
        uiState.overrideInfo?.updatedAt?.takeIf { it > 0L }?.let { timestamp ->
            DateFormat.format("MM-dd HH:mm:ss", timestamp).toString()
        }

    SettingSection(modifier = modifier.padding(top = 16.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
            Text(
                text = "Debug Backend Endpoint",
                color = Color(0xFFB7A5FF),
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "当前构建类型：${uiState.buildType}",
                color = Color.White.copy(alpha = 0.7f),
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "当前生效：${uiState.activeBaseUrl}",
                color = Color.White,
                fontWeight = FontWeight.Medium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            if (uiState.hasOverride) {
                Spacer(Modifier.height(4.dp))
                Text(
                    text = "覆盖地址：${uiState.overrideInfo?.url}",
                    color = Color(0xFF5BE49B),
                    style = MaterialTheme.typography.bodySmall,
                )
                if (lastUpdatedText != null) {
                    Text(
                        text = "更新时间：$lastUpdatedText",
                        color = Color.White.copy(alpha = 0.55f),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            uiState.message?.let { message ->
                Spacer(Modifier.height(8.dp))
                Text(text = message, color = Color(0xFF5BE49B), style = MaterialTheme.typography.bodySmall)
            }

            Spacer(Modifier.height(12.dp))
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                viewModel.quickPresets.forEach { (label, url) ->
                    AssistChip(
                        onClick = { viewModel.applyPreset(url) },
                        label = { Text(label) }
                    )
                }
            }

            if (uiState.hasOverride) {
                Spacer(Modifier.height(12.dp))
                TextButton(onClick = viewModel::resetOverride) {
                    Text(text = "恢复默认", color = Color.White)
                }
            }
        }
    }
}
