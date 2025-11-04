package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R

/** Like 按钮 - 支持选中状态 */
@Composable
private fun LikeButton(
    isSelected: Boolean = false,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .size(24.dp)
            .noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        // 选中状态使用 ic_like_light（带渐变色），未选中状态使用 ic_like_normal
        Icon(
            painter = painterResource(
                if (isSelected) R.drawable.ic_like_light else R.drawable.ic_like_normal
            ),
            contentDescription = "Like",
            modifier = Modifier.size(24.dp),
            tint = Color.Unspecified
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
    Box(
        modifier = modifier
            .size(24.dp)
            .noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        // 选中状态使用 ic_dislike_light（带渐变色），未选中状态使用 ic_dislike_normal
        Icon(
            painter = painterResource(
                if (isSelected) R.drawable.ic_dislike_light else R.drawable.ic_dislike_normal
            ),
            contentDescription = "Dislike",
            modifier = Modifier.size(24.dp),
            tint = Color.Unspecified
        )
    }
}

/** Recall 按钮 */
@Composable
private fun RecallButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .size(24.dp)
            .noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_recall),
            contentDescription = "Recall",
            modifier = Modifier.size(24.dp),
            tint = Color.Unspecified
        )
    }
}

/** Keep Talking 按钮 */
@Composable
private fun KeepTalkingActionButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .size(24.dp)
            .noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_keep_talking),
            contentDescription = "Keep Talking",
            modifier = Modifier.size(24.dp),
            tint = Color.Unspecified
        )
    }
}

/** Image Generate 按钮 */
@Composable
private fun ImageGenerateButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .size(24.dp)
            .noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_image_star),
            contentDescription = "Generate Image",
            modifier = Modifier.size(24.dp),
            tint = Color.Unspecified
        )
    }
}

/** 消息卡片底部操作栏（like, dislike, recall） */
@Composable
internal fun MessageActionBar(
    message: MsgInfo,
    onLike: () -> Unit,
    onDislike: () -> Unit,
    onRecall: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val isLiked = message.userFeedback == MsgInfo.UserFeedback.LIKE
    val isDisliked = message.userFeedback == MsgInfo.UserFeedback.DISLIKE

    // 如果已经执行了任何操作（like/dislike），则隐藏所有按钮
    val hasAnyAction = isLiked || isDisliked

    if (!hasAnyAction) {
        Row(
            modifier = modifier
                .fillMaxWidth()
                .padding(horizontal = 2.dp, vertical = 2.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Like 按钮
            LikeButton(
                isSelected = false,
                onClick = onLike,
            )

            // Dislike 按钮
            DislikeButton(
                isSelected = false,
                onClick = onDislike,
            )
            Spacer(Modifier.weight(1f))
            // Recall 按钮
            RecallButton(onClick = onRecall)
        }
    } else {
        // 如果已经执行了操作，只显示对应的按钮（已选中状态）
        Row(
            modifier = modifier
                .fillMaxWidth()
                .padding(horizontal = 2.dp, vertical = 2.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (isLiked) {
                LikeButton(
                    isSelected = true,
                    onClick = {}, // 已选中状态，不可再次点击
                )
            }
            if (isDisliked) {
                DislikeButton(
                    isSelected = true,
                    onClick = {}, // 已选中状态，不可再次点击
                )
            }
        }
    }
}

/** 消息卡片右下角操作按钮（keep talking, image generate） */
@Composable
internal fun MessageCornerActions(
    message: MsgInfo,
    onKeepTalking: () -> Unit,
    onImageGenerate: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val isLiked = message.userFeedback == MsgInfo.UserFeedback.LIKE
    val isDisliked = message.userFeedback == MsgInfo.UserFeedback.DISLIKE

    // 如果已经执行了任何操作（like/dislike），则隐藏所有按钮
    val hasAnyAction = isLiked || isDisliked

    if (!hasAnyAction) {
        Row(
            modifier = modifier,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            ImageGenerateButton(onClick = onImageGenerate)
            KeepTalkingActionButton(onClick = onKeepTalking)
        }
    }
    // 如果有操作，不显示任何按钮
}
