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
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.getSystemService
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.inty.R
import com.ai.inty.audio.AudioInfo
import com.ai.inty.audio.OpeningPlayState
import com.ai.inty.audio.VoicePlayer
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.MsgInfo
import com.ai.inty.utils.ChatTextFormatter
import com.inty.utils.log.EasyLog

/** 复制文本到剪贴板；这是用于测试功能。 */
private fun debugOnlyCopyToClipboard(context: Context, text: String) {
    val clipboard = context.getSystemService<ClipboardManager>()
    val clip = ClipData.newPlainText("Message", text)
    clipboard?.setPrimaryClip(clip)
}

/** 聊天消息项目组件 */
@Composable
fun ChatItem(item: MsgInfo, isCurrentPage: Boolean = true, chatViewModel: ChatViewModel? = null) {
    runCatching {
            when (item.role) {
                "assistant" -> {
                    ChatItemAI(item, isCurrentPage, chatViewModel)
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
        }
        .onFailure { e ->
            EasyLog.log("Error rendering chat item: ${e.message}", priority = EasyLog.ERROR)
            // 渲染失败时显示错误占位符
            Box(
                modifier =
                    Modifier.fillMaxWidth().height(60.dp).background(Color.Red.copy(alpha = 0.1f))
            ) {
                Text(
                    text = "Message display failed",
                    color = Color.White,
                    modifier = Modifier.align(Alignment.Center),
                )
            }
        }
}

/** AI消息显示组件 */
@Composable
private fun ChatItemAI(
    item: MsgInfo,
    isCurrentPage: Boolean = true,
    chatViewModel: ChatViewModel? = null,
) {
    runCatching {
            Column {
                // 播放器按钮
                if (item.content.isNotEmpty() && item.content != "loading_animation") {
                    // 使用传入的chatViewModel，如果没有则创建一个新的（向后兼容）
                    val viewModel = chatViewModel ?: viewModel<ChatViewModel>()
                    val agentInfo by viewModel.agentInfo.collectAsState()

                    EasyLog.log(
                        "音频LOG测试 ChatItemAI: agentInfo=${agentInfo?.id}, agentName=${agentInfo?.name}, messageId=${item.localMsgId}"
                    )
                    // 解析agentId：优先使用chatViewModel.agentInfo.id，其次使用消息meta中的agentId
                    val vmAgentId = agentInfo?.id
                    val metaAgentId = item.agentId()
                    val safeAgentId = vmAgentId ?: metaAgentId ?: ""
                    EasyLog.log(
                        "音频LOG测试 AgentId resolve: vmAgentId=$vmAgentId, metaAgentId=$metaAgentId, chosen=$safeAgentId"
                    )
                    // 为每个消息生成唯一的测试URL，避免状态混乱
                    val audioInfo =
                        AudioInfo(
                            url = item.audio_url ?: "",
                            title = "Voice Message",
                            artist = "AI Agent",
                            messageId = item.localMsgId, // 使用localMsgId，包含_assistant_标识，用于播放状态管理
                            agentId = safeAgentId,
                            agentName = agentInfo?.name, // 添加Agent名称用于日志分析
                        )

                    // 验证关键参数
                    if (safeAgentId.isEmpty()) {
                        EasyLog.log(
                            "音频LOG测试 Warning: agentId is empty for message: ${item.localMsgId}, vmAgentId=${vmAgentId}, metaAgentId=${metaAgentId}, chatViewModel=${chatViewModel?.hashCode()}",
                            EasyLog.WARN,
                        )
                    } else {
                        EasyLog.log(
                            "音频LOG测试 AudioInfo created successfully: agentId=${audioInfo.agentId}, messageId=${audioInfo.messageId}"
                        )
                    }

                    // 检查queryMsgs是否完成
                    val isQueryMsgsCompleted by viewModel.isQueryMsgsCompleted.collectAsState()

                    // 检查当前消息列表是否只有开场白消息,避免已经聊过多个消息后，再进入还播放开场白
                    val allMessages by viewModel.msgs.collectAsState()
                    // 更准确的消息过滤：只计算实际的聊天消息（排除intro和开场白）
                    val actualChatMessages =
                        allMessages.filter { !it.isOpening() && it.role != "system" }
                    val isOnlyOpeningMessage = actualChatMessages.isEmpty()

                    // 检查开场白是否已播放过
                    val hasPlayedOpening = OpeningPlayState.agentOpeningPlayed(agentInfo?.id ?: "")
                    EasyLog.log(
                        "音频LOG测试 音频消息allMessages.size ${allMessages.size}, actualChatMessages.size ${actualChatMessages.size}, isOnlyOpeningMessage:$isOnlyOpeningMessage, hasPlayedOpening:$hasPlayedOpening, isQueryMsgsCompleted:$isQueryMsgsCompleted ",
                        EasyLog.WARN,
                    )
                    // 开场白自动播放逻辑：只有开场白消息且未播放过，且queryMsgs已完成
                    val shouldAutoPlay =
                        item.isOpening() &&
                            isOnlyOpeningMessage &&
                            !hasPlayedOpening &&
                            isCurrentPage &&
                            isQueryMsgsCompleted &&
                            !(safeAgentId.isEmpty()) &&
                            audioInfo.url.isNotEmpty()

                    EasyLog.log(
                        "音频LOG测试 开场白自动播放判断: shouldAutoPlay=$shouldAutoPlay, isOpening=${item.isOpening()}, isOnlyOpeningMessage=$isOnlyOpeningMessage, hasPlayedOpening=$hasPlayedOpening, isCurrentPage=$isCurrentPage, isQueryMsgsCompleted=$isQueryMsgsCompleted, agentId='${audioInfo.agentId}', hasAudioUrl=${audioInfo.url.isNotEmpty()}",
                        EasyLog.WARN,
                    )
                    if (safeAgentId.isEmpty()) {
                        // agentId 为空时，跳过渲染播放器，避免前置校验导致TTS未调用
                        EasyLog.log(
                            "音频LOG测试 Skip VoicePlayer: empty agentId, messageId=${item.localMsgId}, serverMessageId=${item.id}",
                            EasyLog.WARN,
                        )
                    } else {
                        EasyLog.log(
                            "音频LOG测试 Prepare VoicePlayer: messageId=${item.localMsgId}, serverMessageId=${item.id}, agentId=$safeAgentId, hasAudioUrl=${audioInfo.url.isNotEmpty()}"
                        )
                        VoicePlayer(
                            audioInfo = audioInfo,
                            autoPlay = shouldAutoPlay,
                            modifier = Modifier.widthIn(38.dp),
                            onPlayStateChange = { isPlaying ->
                                EasyLog.log(
                                    "音频LOG测试 VoicePlayer play state changed: $isPlaying for message: ${item.localMsgId}"
                                )
                            },
                            onTtsGenerated = { audioUrl ->
                                // 使用localMsgId进行匹配，因为ChatViewModel中使用的是localMsgId
                                viewModel.updateMessageAudioUrl(item.localMsgId, audioUrl)
                            },
                            serverMessageId = item.id, // 传递服务器端ID用于TTS生成
                        )
                    }
                }
                // 消息
                val msgShape =
                    if (item.content.isNotEmpty() && item.content != "loading_animation")
                        RoundedCornerShape(topEnd = 12.dp, bottomStart = 12.dp, bottomEnd = 12.dp)
                    else RoundedCornerShape(12.dp)

                Row {
                    val context = LocalContext.current
                    Box(
                        modifier =
                            Modifier.background(Color.Black.copy(alpha = 0.5f), msgShape)
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
                                actionColor = Color.White.copy(0.55f),
                            )
                        }
                    }
                    Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
                }
            }
        }
        .onFailure { e ->
            EasyLog.log("Error rendering AI chat item: ${e.message}", priority = EasyLog.ERROR)
            // 渲染失败时显示简化版本
            Row {
                val context = LocalContext.current
                Box(
                    modifier =
                        Modifier.background(
                                Color.Black.copy(alpha = 0.5f),
                                RoundedCornerShape(12.dp),
                            )
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
                        fontSize = 14.sp,
                    )
                }
                Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
            }
        }
}

/** 用户消息显示组件 */
@Composable
private fun ChatItemUser(item: MsgInfo) {
    runCatching {
            Row {
                Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
                val context = LocalContext.current
                Box(
                    modifier =
                        Modifier.background(
                                Color.White.copy(alpha = 0.6f),
                                RoundedCornerShape(12.dp),
                            )
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
                        actionColor = Color(0xff090909).copy(0.6f),
                    )
                }
            }
        }
        .onFailure { e ->
            EasyLog.log("Error rendering user chat item: ${e.message}", priority = EasyLog.ERROR)
            // 渲染失败时显示简化版本
            Row {
                Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
                val context = LocalContext.current
                Box(
                    modifier =
                        Modifier.background(
                                Color.White.copy(alpha = 0.6f),
                                RoundedCornerShape(12.dp),
                            )
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
                        fontSize = 14.sp,
                    )
                }
            }
        }
}

/** 样式化消息文本组件 */
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
                text =
                    ChatTextFormatter.formatChatMessage(
                        text = text,
                        fontSize = fontSize,
                        fontWeight = fontWeight,
                        normalColor = normalColor,
                        italicColor = actionColor,
                    )
            )
        }
        .onFailure { e ->
            EasyLog.log("Error formatting chat message: ${e.message}", priority = EasyLog.ERROR)
            // 格式化失败时显示原始文本
            Text(
                text = text.ifEmpty { "Message content is empty" },
                fontSize = fontSize,
                fontWeight = fontWeight,
                color = normalColor,
            )
        }
}

/** 加载动画组件 */
@Composable
private fun LoadingAnimation() {
    val infiniteTransition = rememberInfiniteTransition(label = "loading")

    Row(
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        repeat(3) { index ->
            val delay = index * 200
            val dotAlpha by
                infiniteTransition.animateFloat(
                    initialValue = 0.3f,
                    targetValue = 1.0f,
                    animationSpec = infiniteRepeatable(animation = tween(600, delayMillis = delay)),
                    label = "dot_alpha_$index",
                )

            Box(
                modifier =
                    Modifier.size(6.dp)
                        .background(color = Color.White.copy(dotAlpha * 0.7f), shape = CircleShape)
            )
        }
    }
}

/** 优化的可折叠文本卡片组件 使用新的ExpandableText组件实现 */
@Composable
fun AgentInfoChatCard(info: String) {

    val str = buildAnnotatedString {
        withStyle(style = SpanStyle(fontWeight = FontWeight.SemiBold)) { append("Intro: ") }
        append(info)
    }

    Box(
        modifier =
            Modifier.background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                .padding(12.dp)
    ) {
        ExpandableTextWithButton(
            text = str,
            collapsedMaxLines = 3,
            textStyle =
                TextStyle(
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                    color = Color.White,
                    fontWeight = FontWeight.Normal,
                ),
        )
    }
}

@Composable
private fun ExpandableTextWithButton(
    text: AnnotatedString,
    modifier: Modifier = Modifier,
    collapsedMaxLines: Int = 3,
    textStyle: TextStyle = TextStyle.Default,
) {
    var isExpanded by remember { mutableStateOf(false) }
    var expandable by remember { mutableStateOf(false) }

    Box(modifier = modifier.fillMaxWidth()) {
        var pd by remember { mutableIntStateOf(0) }
        Text(
            text = text,
            modifier = Modifier.fillMaxWidth().padding(end = pd.dp),
            style = textStyle,
            maxLines = if (isExpanded) Int.MAX_VALUE else collapsedMaxLines,
            overflow = TextOverflow.Ellipsis,
            onTextLayout = { textLayoutResult ->
                if (!isExpanded && textLayoutResult.hasVisualOverflow) {
                    expandable = true
                }
                // 文案过长，需要折叠的时候，才加上bottom的padding
                pd =
                    if (textLayoutResult.lineCount >= 3 && textLayoutResult.hasVisualOverflow) 15
                    else 0
            },
        )
        if (expandable) {
            Icon(
                painter =
                    painterResource(
                        if (isExpanded) R.drawable.ic_arrow_up else R.drawable.ic_arrow_down
                    ),
                contentDescription = null,
                modifier =
                    Modifier.size(18.dp)
                        .align(Alignment.BottomEnd)
                        .noRippleClickable(onClick = { isExpanded = isExpanded.not() }),
                tint = Color.White,
            )
        }
    }
}
