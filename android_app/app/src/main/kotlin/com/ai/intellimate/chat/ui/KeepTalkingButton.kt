package com.ai.intellimate.chat.ui

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R

/** Keep Talking悬浮按钮组件 - 圆形按钮 */
@Composable
fun KeepTalkingFloatingButton(
    visible: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    if (!visible) return
    val buttonSize = 24.dp // 与 like/dislike 按钮高度一致
    val buttonImageSize = 16.dp

    Box(
        modifier = modifier
            .size(buttonSize) // 固定尺寸确保圆形
            .clip(CircleShape) // 圆形
            .background(
                Color.Black.copy(alpha = 0.6f),
                CircleShape
            )
            .noRippleClickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Image(
            painter = painterResource(R.drawable.ic_keep_talking),
            contentDescription = "Keep Talking",
            modifier = Modifier.size(buttonImageSize),
        )
    }
}
