package com.ai.intellimate.chat.ui

import ai.sxwl.android.design.theme.IntelliMateTheme
import androidx.annotation.StringRes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.UiConfigs.ChatMessagePane.AI_WIDTH_RATIO

internal const val OFFICIAL_ASSISTANT_FAQ_MAX_ITEMS = 7

/**
 * 官方助手 FAQ 快捷问题项（Official Assistant FAQ Item）。
 *
 * 使用范围：
 * - 仅用于 IntelliMate 官方助手聊天页的顶部快捷提问区。
 *
 * 预期视觉效果：
 * - 一组纵向排列的短标题按钮；
 * - 整体容器背景使用与 AI 文本消息一致的半透明黑色气泡背景，点击后由上层回填长问题到输入框（不直接发送）。
 *
 * 可配置项：
 *
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
 * - FAQ 按钮纵向排列，避免横向拥挤；
 * - 背景与 AI 消息气泡一致（半透明黑底），按钮文案为短标题。
 *
 * 可配置项：
 *
 * @param modifier 外层布局修饰符（控制间距、宽度、位置）
 * @param items FAQ 项列表（建议最多 9 个）
 * @param onQuestionClick 按钮点击回调（由上层决定如何处理回填）
 */
@Composable
internal fun OfficialAssistantFaqQuestions(
    modifier: Modifier = Modifier,
    items: List<OfficialAssistantFaqItem>,
    onQuestionClick: (OfficialAssistantFaqItem) -> Unit,
) {
    Column(
        modifier =
            modifier
                .fillMaxWidth(AI_WIDTH_RATIO)
                .background(
                    color = Color.Black.copy(alpha = 0.5f),
                    shape = RoundedCornerShape(12.dp),
                )
                .padding(dimensionResource(R.dimen.padding_medium)),
    ) {
        Text(
            text = stringResource(R.string.chat_official_faq_intro),
            style = MaterialTheme.typography.bodyMedium,
            color = Color.White,
        )

        Spacer(Modifier.height(dimensionResource(R.dimen.padding_large)))

        items.forEach { item ->
            Button(
                onClick = { onQuestionClick(item) },
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.surface
                ),
                shape = RoundedCornerShape(100)
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

@Preview(showBackground = true, name = "Official Assistant FAQ")
@Composable
private fun PreviewOfficialAssistantFaqQuestions() {
    IntelliMateTheme {
        Surface(color = MaterialTheme.colorScheme.surface) {
            OfficialAssistantFaqQuestions(
                modifier = Modifier.padding(16.dp),
                items = officialAssistantFaqItems(),
                onQuestionClick = {},
            )
        }
    }
}
