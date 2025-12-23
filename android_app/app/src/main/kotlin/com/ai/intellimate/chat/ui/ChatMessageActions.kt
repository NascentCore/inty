package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/** Like 按钮 - 支持选中状态 */
@Composable
private fun LikeButton(
    isSelected: Boolean = false,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val iconSize = UiConfigs.ChatMessagePane.ActionButtonIconSize
    Box(
        modifier = modifier.size(iconSize).noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        // 选中状态使用 ic_like_light（带渐变色），未选中状态使用 ic_like_normal
        Icon(
            painter =
                painterResource(
                    if (isSelected) R.drawable.ic_like_light else R.drawable.ic_like_normal
                ),
            contentDescription = "Like",
            modifier = Modifier.size(iconSize),
            tint = Color.Unspecified,
        )
    }
}

/** Dislike 按钮 - 支持选中状态 */
@Composable
private fun DislikeButton(
    isSelected: Boolean = false,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val iconSize = UiConfigs.ChatMessagePane.ActionButtonIconSize
    Box(
        modifier = modifier.size(iconSize).noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        // 选中状态使用 ic_dislike_light（带渐变色），未选中状态使用 ic_dislike_normal
        Icon(
            painter =
                painterResource(
                    if (isSelected) R.drawable.ic_dislike_light else R.drawable.ic_dislike_normal
                ),
            contentDescription = "Dislike",
            modifier = Modifier.size(iconSize),
            tint = Color.Unspecified,
        )
    }
}

/** Recall 按钮 */
@Composable
private fun RecallButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val iconSize = UiConfigs.ChatMessagePane.ActionButtonIconSize
    Box(
        modifier = modifier.size(iconSize).noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_recall),
            contentDescription = "Recall",
            modifier = Modifier.size(iconSize),
            tint = Color.Unspecified,
        )
    }
}

/** Image Generate 按钮 */
@Composable
private fun ImageGenerateButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val iconSize = UiConfigs.ChatMessagePane.ActionButtonIconSize
    Box(
        modifier = modifier.size(iconSize).noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_image_star),
            contentDescription = "Generate Image",
            modifier = Modifier.size(iconSize),
            tint = Color.Unspecified,
        )
    }
}

@Composable
private fun EmojiButton(
    emoji: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    alpha: Float = 1f,
) {
    val fontSize = UiConfigs.ChatMessagePane.ReactionEmoji.FontSize
    Box(
        modifier = modifier.noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = emoji,
            style =
                TextStyle(
                    fontSize = fontSize,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = alpha),
                ),
            maxLines = 1,
            overflow = TextOverflow.Clip,
        )
    }
}

@Composable
private fun ReactionEmojiPicker(
    emojis: List<String>,
    onEmojiClick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val cfg = UiConfigs.ChatMessagePane.ReactionEmoji
    val shape = RoundedCornerShape(cfg.PickerCornerRadius)
    Row(
        modifier =
            modifier
                .background(
                    color = Color.White.copy(alpha = cfg.PickerBackgroundAlpha),
                    shape = shape,
                )
                .border(
                    width = cfg.PickerBorderWidth,
                    color = Color.White.copy(alpha = cfg.PickerBorderAlpha),
                    shape = shape,
                )
                .padding(
                    horizontal = cfg.PickerHorizontalPadding,
                    vertical = cfg.PickerVerticalPadding,
                ),
        horizontalArrangement = Arrangement.spacedBy(cfg.PickerItemSpacing),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        emojis.forEach { emoji ->
            EmojiButton(
                emoji = emoji,
                onClick = { onEmojiClick(emoji) },
            )
        }
    }
}

/** 消息卡片底部操作栏（like, dislike, recall） */
@Composable
internal fun MessageActionBar(
    message: MsgInfo,
    onLike: () -> Unit,
    onDislike: () -> Unit,
    onRecall: () -> Unit,
    reactions: List<String>,
    onAddReaction: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val isLiked = message.userFeedback == MsgInfo.UserFeedback.LIKE
    val isDisliked = message.userFeedback == MsgInfo.UserFeedback.DISLIKE
    val cfg = UiConfigs.ChatMessagePane.ReactionEmoji

    // 需求：点击灰色 😀 弹出 emoji 列表；选中后追加到灰色 😀 左侧，可重复追加多个。
    var showPicker by remember(message.localMsgId) { mutableStateOf(false) }
    val emojiOptions =
        remember {
            listOf(
                "😀",
                "😭",
                "😁",
                "😜",
                "😂",
                "💕",
                "❤️",
                "💯",
                "💪",
                "😍",
                "🥳",
                "✨",
                "🎊",
                "💘",
                "💌",
                "💓",
                "👅",
                "👩‍❤️‍👨",
                "🌹",
                "🥀",
            )
        }

    // like/dislike互斥，但不影响recall和keep talking的状态
    Column(modifier = modifier.fillMaxWidth().padding(horizontal = 2.dp, vertical = 2.dp)) {
        if (showPicker) {
            ReactionEmojiPicker(
                emojis = emojiOptions,
                onEmojiClick = { emoji ->
                    onAddReaction(emoji)
                    showPicker = false
                },
                modifier = Modifier.padding(bottom = cfg.PickerToActionsSpacing),
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement =
                Arrangement.spacedBy(UiConfigs.ChatMessagePane.ActionButtonSpacing),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Like 按钮 - 如果已dislike则不显示
            if (!isDisliked) {
                LikeButton(
                    isSelected = isLiked,
                    onClick =
                        if (isLiked) {
                            {}
                        } else onLike, // 已选中状态，不可再次点击
                )
            }

            // Dislike 按钮 - 如果已like则不显示
            if (!isLiked) {
                DislikeButton(
                    isSelected = isDisliked,
                    onClick =
                        if (isDisliked) {
                            {}
                        } else onDislike, // 已选中状态，不可再次点击
                )
            }

            // 已选 emoji：显示在灰色 😀 左侧（可追加多个）
            reactions.forEach { emoji ->
                EmojiButton(
                    emoji = emoji,
                    onClick = {},
                    modifier = Modifier,
                    alpha = 1f,
                )
            }

            // 灰色 😀 占位 + 按钮：点击展开 emoji 列表
            EmojiButton(
                emoji = "😀",
                onClick = { showPicker = !showPicker },
                alpha = cfg.PlaceholderAlpha,
            )

            Spacer(Modifier.weight(1f))

            // Recall 按钮 - 始终显示，不受like/dislike影响
            //        RecallButton(onClick = onRecall)
        }
    }
}

/** 消息卡片右下角操作按钮（image generate） */
@Composable
internal fun MessageCornerActions(onImageGenerate: () -> Unit, modifier: Modifier = Modifier) {
    // image generate不受like/dislike影响，始终显示
    // keep talking按钮已移至ChatInput右上角悬浮
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(UiConfigs.ChatMessagePane.ActionButtonSpacing),
    ) {
        ImageGenerateButton(onClick = onImageGenerate)
    }
}
