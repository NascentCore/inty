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
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.material3.Text
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/** Like 按钮 - 支持选中状态 */
@Composable
private fun LikeButton(
    modifier: Modifier = Modifier,
    isSelected: Boolean = false,
    onClick: () -> Unit,
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
    modifier: Modifier = Modifier,
    isSelected: Boolean = false,
    onClick: () -> Unit,
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
fun ImageGenerateButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
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
    isGray: Boolean = false,
) {
    val fontSize = UiConfigs.ChatMessagePane.ReactionEmoji.FontSize
    
    Box(
        modifier = modifier
            .noRippleClickable(onClick = onClick)
            .then(
                if (isGray) {
                    // 使用 drawWithContent 应用灰度效果
                    Modifier.drawWithContent {
                        // 先绘制内容
                        drawContent()
                        // 然后应用灰度遮罩：使用 BlendMode.Saturation 降低饱和度
                        drawRect(
                            color = Color.Gray.copy(alpha = 0.5f),
                            blendMode = BlendMode.Saturation
                        )
                    }
                } else {
                    Modifier
                }
            ),
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
                "👍",
                "👎",
                "😍",
                "😁",
                "😜",
                "😂",
                "❤️",
                "💯",
                "💘",
                "🌹",
            )
        }

    // like/dislike互斥，但不影响recall和keep talking的状态
    Box(modifier = modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 2.dp, vertical = 2.dp)
                .then(
                    if (showPicker) {
                        // 当 picker 显示时，添加点击检测来关闭 picker
                        // 注意：点击 picker 和按钮区域不会触发关闭，因为 Row 上的 pointerInput 会阻止事件传播
                        Modifier.pointerInput(true) {
                            detectTapGestures {
                                // 点击外部区域，关闭 picker
                                showPicker = false
                            }
                        }
                    } else {
                        Modifier
                    }
                )
        ) {
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
                reactions.forEachIndexed { index, emoji ->
                    key("emoji_${index}_$emoji") {
                        EmojiButton(
                            emoji = emoji,
                            onClick = {},
                            modifier = Modifier,
                            alpha = 1f,
                        )
                    }
                }

                // 灰色 😀 占位 + 按钮：点击展开 emoji 列表
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.pointerInput(showPicker) {
                        // 阻止点击事件传播，防止关闭 picker
                        detectTapGestures { }
                    },
                ) {
                    EmojiButton(
                        emoji = "😀",
                        onClick = { showPicker = !showPicker },
                        alpha = cfg.PlaceholderAlpha,
                        isGray = true, // 灰色占位按钮
                    )
                    
                    // emoji 选择器显示在按钮下方，与按钮中心对齐
                    if (showPicker) {
                        ReactionEmojiPicker(
                            emojis = emojiOptions,
                            onEmojiClick = { emoji ->
                                onAddReaction(emoji)
                                showPicker = false
                            },
                            modifier = Modifier.padding(top = cfg.PickerToActionsSpacing),
                        )
                    }
                }

                Spacer(Modifier.weight(1f))

                // Recall 按钮 - 始终显示，不受like/dislike影响
                //        RecallButton(onClick = onRecall)
            }
        }
    }
}
