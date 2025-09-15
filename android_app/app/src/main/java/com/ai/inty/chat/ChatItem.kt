package com.ai.inty.chat

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.inty.audio.AudioInfo
import com.ai.inty.audio.OpeningPlayState
import com.ai.inty.audio.VoicePlayer
import com.ai.inty.beans.MsgInfo
import com.ai.inty.utils.ChatTextFormatter
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.log.EasyLog

/**
 * 复制文本到剪贴板；这是用于测试功能。
 */
private fun debugOnlyCopyToClipboard(context: Context, text: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    val clip = ClipData.newPlainText("Message", text)
    clipboard.setPrimaryClip(clip)
}

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
        Column {
            //播放器按钮
            if (item.content.isNotEmpty() && item.content != "loading_animation") {
                val viewModel = viewModel<ChatViewModel>()
                val agentInfo by viewModel.agentInfo.collectAsState()

                // 为每个消息生成唯一的测试URL，避免状态混乱
                val audioInfo = AudioInfo(
                    url = item.audio_url ?: "",
                    title = "Voice Message",
                    artist = "AI Agent",
                    messageId = item.localMsgId, // 使用localMsgId，包含_assistant_标识，用于播放状态管理
                    agentId = agentInfo?.id // 使用当前agent的ID
                )

                val hasPlayedOpening = OpeningPlayState.agentOpeningPlayed(agentInfo?.id ?: "")

                // 检查当前消息列表是否只有开场白消息
                val allMessages by viewModel.msgs.collectAsState()
                val isOnlyOpeningMessage =
                    allMessages.size == 1 && allMessages.firstOrNull()?.isOpening() == true

                val shouldAutoPlay =
                    item.isOpening() && hasPlayedOpening.not() && isOnlyOpeningMessage

                VoicePlayer(
                    audioInfo = audioInfo,
                    autoPlay = shouldAutoPlay,
                    modifier = Modifier
                        .height(26.dp)
                        .widthIn(48.dp),
                    onPlayStateChange = { isPlaying ->
                        agentInfo?.id?.let { id ->
                            if (isPlaying) OpeningPlayState.openingPlayedAsync(id)
                        }
                    },
                    onTtsGenerated = { audioUrl ->
                        // TTS生成成功，更新消息的音频URL
                        // 使用localMsgId进行匹配，因为ChatViewModel中使用的是localMsgId
                        viewModel.updateMessageAudioUrl(item.localMsgId, audioUrl)
                    },
                    serverMessageId = item.id // 传递服务器端ID用于TTS生成
                )
            }
            //消息
            Row {
                val context = LocalContext.current
                Box(
                    modifier = Modifier
                        .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                        .padding(12.dp, 13.dp)
                        .widthIn(1.dp, 300.dp)
                        .pointerInput(item.content) {
                            detectTapGestures(
                                onLongPress = {
                                    debugOnlyCopyToClipboard(context, item.content)
                                }
                            )
                        }
                ) {
                    if (item.content == "loading_animation") {
                        LoadingAnimation()
                    } else {
                        // 消息文本
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

    }.onFailure { e ->
        EasyLog.log("Error rendering AI chat item: ${e.message}", priority = EasyLog.ERROR)
        // 渲染失败时显示简化版本
        Row {
            val context = LocalContext.current
            Box(
                modifier = Modifier
                    .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                    .padding(12.dp, 13.dp)
                    .widthIn(1.dp, 300.dp)
                    .pointerInput(item.content) {
                        detectTapGestures(
                            onLongPress = {
                                debugOnlyCopyToClipboard(context, item.content)
                            }
                        )
                    }
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
            val context = LocalContext.current
            Box(
                modifier = Modifier
                    .background(Color.White.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
                    .padding(12.dp, 13.dp)
                    .widthIn(1.dp, 300.dp)
                    .pointerInput(item.content) {
                        detectTapGestures(
                            onLongPress = {
                                debugOnlyCopyToClipboard(context, item.content)
                            }
                        )
                    }
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
            val context = LocalContext.current
            Box(
                modifier = Modifier
                    .background(Color.White.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
                    .padding(12.dp, 13.dp)
                    .widthIn(1.dp, 300.dp)
                    .pointerInput(item.content) {
                        detectTapGestures(
                            onLongPress = {
                                debugOnlyCopyToClipboard(context, item.content)
                            }
                        )
                    }
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
    fontSize: TextUnit,
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
    val infiniteTransition = rememberInfiniteTransition(label = "loading")

    Row(
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        repeat(3) { index ->
            val delay = index * 200
            val dotAlpha by infiniteTransition.animateFloat(
                initialValue = 0.3f,
                targetValue = 1.0f,
                animationSpec = infiniteRepeatable(
                    animation = tween(600, delayMillis = delay)
                ), label = "dot_alpha_$index"
            )

            Box(
                modifier = Modifier
                    .size(6.dp)
                    .background(
                        color = Color.White.copy(dotAlpha * 0.7f),
                        shape = CircleShape
                    )
            )
        }
    }
} 
