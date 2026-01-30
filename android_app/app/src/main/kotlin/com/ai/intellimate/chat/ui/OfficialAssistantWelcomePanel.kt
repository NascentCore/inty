package com.ai.intellimate.chat.ui

import ai.sxwl.android.design.noRippleClickable
import androidx.annotation.StringRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.ai.intellimate.ui.UiConfigs

/** 官方助手快捷入口配置项 */
data class OfficialAssistantShortcut(
    @StringRes val labelResId: Int,
    @StringRes val promptResId: Int,
)

/**
 * IntelliMate 官方助手欢迎面板（CREATED_BY_AGENT）。
 *
 * 使用范围：仅用于官方 IntelliMate 角色聊天页在无历史对话时的引导展示。
 * 预期视觉效果：顶部问候文案 + 右侧应用头像，下方提供多枚圆角快捷入口，整体风格类似 Gemini 首屏。
 * 可配置项：标题、副标题、应用图标资源、快捷入口列表、点击回调用于预填提示词，以及外部 Modifier。
 */
@Composable
@OptIn(ExperimentalLayoutApi::class)
fun OfficialAssistantWelcomePanel(
    title: String,
    subtitle: String,
    appIconResId: Int,
    shortcuts: List<OfficialAssistantShortcut>,
    onShortcutClick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f, fill = false)) {
                Text(
                    text = title,
                    fontSize = UiConfigs.Typography.Title,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Spacer(Modifier.height(UiConfigs.ChatPage.OfficialAssistant.TitleSubtitleSpacing))
                Text(
                    text = subtitle,
                    fontSize = UiConfigs.Typography.BodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Image(
                painter = painterResource(id = appIconResId),
                contentDescription = null,
                modifier =
                    Modifier.size(UiConfigs.ChatPage.OfficialAssistant.HeaderIconSize)
                        .clip(CircleShape),
            )
        }

        Spacer(Modifier.height(UiConfigs.ChatPage.OfficialAssistant.HeaderToShortcutSpacing))

        FlowRow(
            horizontalArrangement =
                Arrangement.spacedBy(UiConfigs.ChatPage.OfficialAssistant.ShortcutChipHorizontalSpacing),
            verticalArrangement =
                Arrangement.spacedBy(UiConfigs.ChatPage.OfficialAssistant.ShortcutChipVerticalSpacing),
        ) {
            shortcuts.forEach { shortcut ->
                val label = stringResource(id = shortcut.labelResId)
                val prompt = stringResource(id = shortcut.promptResId)
                Box(
                    modifier =
                        Modifier.clip(
                                RoundedCornerShape(
                                    UiConfigs.ChatPage.OfficialAssistant.ShortcutChipCornerRadius
                                )
                            )
                            .background(MaterialTheme.colorScheme.surfaceContainerLow)
                            .noRippleClickable { onShortcutClick(prompt) },
                ) {
                    Text(
                        text = label,
                        fontSize = UiConfigs.Typography.Body,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier =
                            Modifier.padding(
                                horizontal =
                                    UiConfigs.ChatPage.OfficialAssistant
                                        .ShortcutChipHorizontalPadding,
                                vertical =
                                    UiConfigs.ChatPage.OfficialAssistant
                                        .ShortcutChipVerticalPadding,
                            ),
                    )
                }
            }
        }
    }
}
