package com.ai.intellimate.chat.ui

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R

/** Keep Talking悬浮按钮组件 - 固定在ChatInput上方，右侧紧贴屏幕 */
@Composable
fun KeepTalkingFloatingButton(
    visible: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    if (!visible) return

    Box(
        modifier = modifier
            .clip(
                RoundedCornerShape(
                    topStart = 20.dp,
                    bottomStart = 20.dp
                )
            ) // 左侧半圆角，右侧直角
            .background(
                Color.Black.copy(alpha = 0.6f),
                RoundedCornerShape(topStart = 20.dp, bottomStart = 20.dp)
            )
            .noRippleClickable(onClick = onClick)
            .padding(4.dp),
        contentAlignment = Alignment.Center,
    ) {
        Image(
            painter = painterResource(R.drawable.ic_keep_talking),
            contentDescription = "Keep Talking",
            modifier = Modifier.size(18.dp),
        )
    }
}
