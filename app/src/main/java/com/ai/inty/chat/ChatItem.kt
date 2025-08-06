package com.ai.inty.chat

import androidx.compose.animation.core.animateFloat
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.beans.MsgInfo
import com.ai.inty.utils.ChatTextFormatter
import com.inty.utils.log.EasyLog

/**
 * 聊天消息项目组件
 */
@Composable
fun ChatItem(item: MsgInfo) {
    when (item.role) {
        "assistant" -> {
            ChatItemAI(item)
        }

        "user" -> {
            ChatItemUser(item)
        }

        else -> {
            EasyLog.log("unknown role: $item")
        }
    }
}

/**
 * AI消息显示组件
 */
@Composable
private fun ChatItemAI(item: MsgInfo) {
    Row {
        Box(
            modifier = Modifier
                .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                .padding(12.dp, 13.dp)
                .widthIn(1.dp, 300.dp)
        ) {
            if (item.content == "loading_animation") {
                LoadingAnimation()
            } else {
                StyledMessageText(
                    text = item.content,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Normal,
                    normalColor = Color.White,
                    actionColor = Color.White.copy(0.55f)
                )
            }
        }
        Spacer(
            modifier = Modifier
                .widthIn(80.dp)
                .weight(1f)
        )
    }
}

/**
 * 用户消息显示组件
 */
@Composable
private fun ChatItemUser(item: MsgInfo) {
    Row {
        Spacer(
            modifier = Modifier
                .widthIn(80.dp)
                .weight(1f)
        )
        Box(
            modifier = Modifier
                .background(Color.White.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
                .padding(12.dp, 13.dp)
                .widthIn(1.dp, 300.dp)
        ) {
            StyledMessageText(
                text = item.content,
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
                normalColor = Color(0xff090909),
                actionColor = Color(0xff090909).copy(0.6f)
            )
        }
    }
}

/**
 * 样式化消息文本组件
 */
@Composable
private fun StyledMessageText(
    text: String,
    fontSize: androidx.compose.ui.unit.TextUnit,
    fontWeight: FontWeight,
    normalColor: Color,
    actionColor: Color,
) {
    Text(
        text = ChatTextFormatter.formatChatMessage(
            text = text,
            fontSize = fontSize,
            fontWeight = fontWeight,
            normalColor = normalColor,
            italicColor = actionColor
        )
    )
}

/**
 * 加载动画组件
 */
@Composable
private fun LoadingAnimation() {
    val infiniteTransition =
        androidx.compose.animation.core.rememberInfiniteTransition(label = "loading")

    Row(
        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(4.dp),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        repeat(3) { index ->
            val delay = index * 200
            val dotAlpha by infiniteTransition.animateFloat(
                initialValue = 0.3f,
                targetValue = 1.0f,
                animationSpec = androidx.compose.animation.core.infiniteRepeatable(
                    animation = androidx.compose.animation.core.tween(600, delayMillis = delay)
                ), label = "dot_alpha_$index"
            )

            Box(
                modifier = Modifier
                    .size(6.dp)
                    .background(
                        color = Color.White.copy(dotAlpha * 0.7f),
                        shape = androidx.compose.foundation.shape.CircleShape
                    )
            )
        }
    }
} 
