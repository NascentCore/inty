package com.ai.intellimate.chat.ui

import androidx.annotation.StringRes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.foundation.shape.RoundedCornerShape
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

internal const val OFFICIAL_ASSISTANT_FAQ_MAX_ITEMS = 9

/**
 * 官方助手 FAQ 快捷问题项（Official Assistant FAQ Item）。
 *
 * 使用范围：
 * - 仅用于 IntelliMate 官方助手聊天页的顶部快捷提问区。
 *
 * 预期视觉效果：
 * - 一组可换行的胶囊描边按钮，外观接近客服 FAQ 快捷入口；
 * - 点击后触发回调，由上层把“长问题”写入聊天输入框（不直接发送）。
 *
 * 可配置项：
 * @param titleResId 按钮短标题文案资源 ID（展示给用户）
 * @param questionResId 长问题文案资源 ID（回填到输入框）
 */
internal data class OfficialAssistantFaqItem(
    @StringRes val titleResId: Int,
    @StringRes val questionResId: Int,
)

internal fun officialAssistantFaqItems(): List<OfficialAssistantFaqItem> {
    return listOf(
        OfficialAssistantFaqItem(
            titleResId = R.string.chat_official_faq_title_restore_premium,
            questionResId = R.string.chat_official_faq_question_restore_premium,
        ),
        OfficialAssistantFaqItem(
            titleResId = R.string.chat_official_faq_title_fix_voice_call,
            questionResId = R.string.chat_official_faq_question_fix_voice_call,
        ),
        OfficialAssistantFaqItem(
            titleResId = R.string.chat_official_faq_title_upscale_image,
            questionResId = R.string.chat_official_faq_question_upscale_image,
        ),
        OfficialAssistantFaqItem(
            titleResId = R.string.chat_official_faq_title_create_imate,
            questionResId = R.string.chat_official_faq_question_create_imate,
        ),
        OfficialAssistantFaqItem(
            titleResId = R.string.chat_official_faq_title_daily_chat_limit,
            questionResId = R.string.chat_official_faq_question_daily_chat_limit,
        ),
        OfficialAssistantFaqItem(
            titleResId = R.string.chat_official_faq_title_report_issue,
            questionResId = R.string.chat_official_faq_question_report_issue,
        ),
        OfficialAssistantFaqItem(
            titleResId = R.string.chat_official_faq_title_check_version,
            questionResId = R.string.chat_official_faq_question_check_version,
        ),
    )
}

/**
 * 官方助手 FAQ 快捷按钮区（Official Assistant FAQ Quick Questions）。
 *
 * 使用范围：
 * - 放置于官方助手聊天页中上部区域，作为“快速提问”入口。
 *
 * 预期视觉效果：
 * - 胶囊描边按钮自动换行排列，按钮文案为短标题；
 * - 整体风格与聊天场景一致（使用 MaterialTheme 的颜色与排版）。
 *
 * 可配置项：
 * @param modifier 外层布局修饰符（控制间距、宽度、位置）
 * @param items FAQ 项列表（建议最多 9 个）
 * @param onQuestionClick 按钮点击回调（由上层决定如何处理回填）
 */
@Composable
@OptIn(ExperimentalLayoutApi::class)
internal fun OfficialAssistantFaqQuestions(
    modifier: Modifier,
    items: List<OfficialAssistantFaqItem>,
    onQuestionClick: (OfficialAssistantFaqItem) -> Unit,
) {
    FlowRow(
        modifier = modifier,
        horizontalArrangement =
            Arrangement.spacedBy(UiConfigs.ChatPage.OfficialAssistantFaq.HorizontalSpacing),
        verticalArrangement =
            Arrangement.spacedBy(UiConfigs.ChatPage.OfficialAssistantFaq.VerticalSpacing),
    ) {
        items.forEach { item ->
            OutlinedButton(
                onClick = { onQuestionClick(item) },
                shape = RoundedCornerShape(UiConfigs.ChatPage.OfficialAssistantFaq.ButtonCornerRadius),
                border =
                    BorderStroke(
                        width = UiConfigs.ChatPage.OfficialAssistantFaq.BorderWidth,
                        color =
                            MaterialTheme.colorScheme.primary.copy(
                                alpha = UiConfigs.ChatPage.OfficialAssistantFaq.BorderAlpha
                            ),
                    ),
                colors =
                    ButtonDefaults.outlinedButtonColors(
                        containerColor =
                            MaterialTheme.colorScheme.surface.copy(
                                alpha = UiConfigs.ChatPage.OfficialAssistantFaq.ButtonBackgroundAlpha
                            ),
                        contentColor = MaterialTheme.colorScheme.primary,
                    ),
                contentPadding =
                    PaddingValues(
                        horizontal = UiConfigs.ChatPage.OfficialAssistantFaq.ButtonHorizontalPadding,
                        vertical = UiConfigs.ChatPage.OfficialAssistantFaq.ButtonVerticalPadding,
                    ),
            ) {
                Text(
                    text = stringResource(item.titleResId),
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = UiConfigs.ChatPage.OfficialAssistantFaq.ButtonTextMaxLines,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}
