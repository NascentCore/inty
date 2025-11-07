package com.ai.intellimate.chat.ui

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R

/** Keep Talking悬浮按钮组件 - 固定在ChatInput上方，右侧紧贴屏幕 */
@Composable
fun KeepTalkingFloatingButton(
    modifier: Modifier = Modifier,
    visible: Boolean,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    if (!visible) return

    val cornerShape = RoundedCornerShape(topStart = 20.dp, bottomStart = 20.dp)
    Box(
        modifier = modifier
            .clip(cornerShape)
            .border(
                1.dp, brush = Brush.horizontalGradient(
                    colors =
                        listOf(
                            Color.White.copy(if (enabled) .7f else .3f),
                            Color.White.copy(.2f),
                        )
                ), shape = cornerShape
            )
            .background(
                Color.Black.copy(alpha = 0.6f),
                cornerShape
            )
            .alpha(if (enabled) 1f else 0.5f)
            .then(
                if (enabled) {
                    Modifier.noRippleClickable(onClick = onClick)
                } else {
                    Modifier
                }
            )
            .padding(4.dp),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_keep_talking),
            contentDescription = "Keep Talking",
            modifier = Modifier.size(20.dp),
            tint = if (enabled) Color.White else Color.LightGray
        )
    }
}
