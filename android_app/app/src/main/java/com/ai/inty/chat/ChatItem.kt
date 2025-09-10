package com.ai.inty.chat

import androidx.compose.animation.core.animateFloat
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.audio.AudioInfo
import com.ai.inty.audio.VoicePlayer
import com.ai.inty.beans.MsgInfo
import com.ai.inty.utils.ChatTextFormatter
import com.inty.utils.log.EasyLog

/**
 * 聊天消息项目组件
 */
@Composable
fun ChatItem(item: MsgInfo) {
    runCatching {
        when (item.role) {
            "assistant" -> {
                ChatItemAI(item)
            }

            "user" -> {
                ChatItemUser(item)
            }

            else -> {
                EasyLog.log("unknown role: $item")
                // 未知角色的消息显示为普通文本
                ChatItemUser(item)
            }
        }
    }.onFailure { e ->
        EasyLog.log("Error rendering chat item: ${e.message}", priority = EasyLog.ERROR)
        // 渲染失败时显示错误占位符
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp)
                .background(Color.Red.copy(alpha = 0.1f))
        ) {
            Text(
                text = "Message display failed",
                color = Color.White,
                modifier = Modifier.align(Alignment.Center)
            )
        }
    }
}

/**
 * AI消息显示组件
 */
@Composable
private fun ChatItemAI(item: MsgInfo) {
    runCatching {
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
                    Column(
                        verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(
                            8.dp
                        )
                    ) {
                        // 消息文本
                        StyledMessageText(
                            text = item.content,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Normal,
                            normalColor = Color.White,
                            actionColor = Color.White.copy(0.55f)
                        )

                        // 语音播放器（仅对AI消息显示）
                        if (item.content != "loading_animation" && item.content.isNotEmpty()) {
                            // 为每个消息生成唯一的测试URL，避免状态混乱
                            val audioInfo = AudioInfo(
                                url = "http://demo.fengxianqi.com/audio/static/opus.opus?msgId=${item.msgId}", // 添加消息ID参数
                                title = "语音消息",
                                artist = "AI助手",
                                messageId = item.msgId,
                                agentId = null // MsgInfo中没有agentId字段，暂时设为null
                            )

                            VoicePlayer(
                                audioInfo = audioInfo,
                                autoPlay = false,
                                showProgress = true,
                                compact = true
                            )
                        }
                    }
                }
            }
            Spacer(
                modifier = Modifier
                    .widthIn(80.dp)
                    .weight(1f)
            )
        }
    }.onFailure { e ->
        EasyLog.log("Error rendering AI chat item: ${e.message}", priority = EasyLog.ERROR)
        // 渲染失败时显示简化版本
        Row {
            Box(
                modifier = Modifier
                    .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                    .padding(12.dp, 13.dp)
                    .widthIn(1.dp, 300.dp)
            ) {
                Text(
                    text = item.content.ifEmpty { "Message content is empty" },
                    color = Color.White,
                    fontSize = 14.sp
                )
            }
            Spacer(
                modifier = Modifier
                    .widthIn(80.dp)
                    .weight(1f)
            )
        }
    }
}

/**
 * 用户消息显示组件
 */
@Composable
private fun ChatItemUser(item: MsgInfo) {
    runCatching {
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
    }.onFailure { e ->
        EasyLog.log("Error rendering user chat item: ${e.message}", priority = EasyLog.ERROR)
        // 渲染失败时显示简化版本
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
                Text(
                    text = item.content.ifEmpty { "Message content is empty" },
                    color = Color(0xff090909),
                    fontSize = 14.sp
                )
            }
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
    runCatching {
        Text(
            text = ChatTextFormatter.formatChatMessage(
                text = text,
                fontSize = fontSize,
                fontWeight = fontWeight,
                normalColor = normalColor,
                italicColor = actionColor
            )
        )
    }.onFailure { e ->
        EasyLog.log("Error formatting chat message: ${e.message}", priority = EasyLog.ERROR)
        // 格式化失败时显示原始文本
        Text(
            text = text.ifEmpty { "Message content is empty" },
            fontSize = fontSize,
            fontWeight = fontWeight,
            color = normalColor
        )
    }
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
