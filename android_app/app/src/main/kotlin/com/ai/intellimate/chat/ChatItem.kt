package com.ai.intellimate.chat

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.LogUtils
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
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
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.getSystemService
import androidx.lifecycle.viewmodel.compose.viewModel
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.audio.AudioInfo
import com.ai.intellimate.audio.OpeningPlayState
import com.ai.intellimate.audio.VoicePlayer
import com.ai.intellimate.chat.ui.FullScreenImageViewer
import com.ai.intellimate.chat.ui.MessageActionBar
import com.ai.intellimate.chat.ui.MessageCornerActions
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.utils.ChatTextFormatter

/** 复制文本到剪贴板；这是用于测试功能。 */
private fun debugOnlyCopyToClipboard(context: Context, text: String) {
    val clipboard = context.getSystemService<ClipboardManager>()
    val clip = ClipData.newPlainText("Message", text)
    clipboard?.setPrimaryClip(clip)
}

/** 聊天消息项目组件 */
@Composable
fun ChatItem(
    item: MsgInfo,
    isCurrentPage: Boolean = true,
    chatViewModel: ChatViewModel? = null,
    isLatestMessage: Boolean = false, // 是否为最后一条AI消息
) {
    runCatching {
        when (item.role) {
            "assistant" -> {
                ChatItemAI(item, isCurrentPage, chatViewModel, isLatestMessage)
            }

            "user" -> {
                ChatItemUser(item)
            }

            else -> {
                LogUtils.i("unknown role: $item")
                // 未知角色的消息显示为普通文本
                ChatItemUser(item)
            }
        }
    }
        .onFailure { e ->
            LogUtils.e("Error rendering chat item: ${e.message}")
            // 渲染失败时显示错误占位符
            Box(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .height(60.dp)
                        .background(Color.Red.copy(alpha = 0.1f))
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
    isLatestMessage: Boolean = false, // 是否为最后一条AI消息
) {
    val viewModel = chatViewModel ?: viewModel<ChatViewModel>()

    runCatching {
        Column(modifier = Modifier.fillMaxWidth(.9f)) {
            // 播放器按钮
            if (item.content.isNotEmpty() && item.content != "loading_animation") {
                val agentInfo by viewModel.agentInfo.collectAsState()

                // 解析agentId：优先使用chatViewModel.agentInfo.id，其次使用消息meta中的agentId
                val vmAgentId = agentInfo?.id
                val metaAgentId = item.agentId()
                val safeAgentId = vmAgentId ?: metaAgentId ?: ""

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

                // 开场白自动播放逻辑：只有开场白消息且未播放过，且queryMsgs已完成，且用户开启了自动播放
                val shouldAutoPlay =
                    item.isOpening() &&
                            isOnlyOpeningMessage &&
                            !hasPlayedOpening &&
                            isCurrentPage &&
                            isQueryMsgsCompleted &&
                            !(safeAgentId.isEmpty()) &&
                            audioInfo.url.isNotEmpty() &&
                            IntySetting.isAutoPlayAudio()

                if (safeAgentId.isNotEmpty()) {
                    VoicePlayer(
                        audioInfo = audioInfo,
                        autoPlay = shouldAutoPlay,
                        modifier = Modifier.widthIn(38.dp),
                        onPlayStateChange = { isPlaying ->
                            LogUtils.d(
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

            // 检查是否有生成的图片（包括loading状态）
            // 图片消息：content为空且meta_data中有generatedImage
            // loading消息：content为"loading_animation"且localMsgId包含"loading_image"
            val hasGeneratedImage = item.hasGeneratedImage()
            val generatedImageUrl = item.getGeneratedImageUrl()
            // 判断是否为图片loading状态：content为"loading_animation"且localMsgId包含"loading_image"
            val isImageLoading = item.content == "loading_animation" &&
                    item.localMsgId.contains("loading_image", ignoreCase = true)
            // 判断是否为图片消息（纯图片，无文本）
            val isImageOnlyMessage = item.content.isEmpty() && hasGeneratedImage

            // 全屏图片查看器状态
            var showFullScreenImage by remember { mutableStateOf(false) }
            // 图片加载错误状态
            var imageLoadError by remember { mutableStateOf(false) }

            // 文本消息内容
            // 图片loading时或纯图片消息时，不显示文本Box，只显示shimmer占位或图片
            if (!isImageLoading && !isImageOnlyMessage) {
                Box(
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row {
                        val context = LocalContext.current
                        Box(
                            modifier =
                                Modifier
                                    .background(Color.Black.copy(alpha = 0.5f), msgShape)
                                    .padding(12.dp, 13.dp)
                                    .widthIn(1.dp, 300.dp)
                                    .then(
                                        if (item.content == "图片生成失败" && item.localMsgId.contains(
                                                "image_error",
                                                ignoreCase = true
                                            )
                                        ) {
                                            // 图片生成失败的消息可点击删除
                                            Modifier.noRippleClickable {
                                                viewModel.deleteMessage(item.localMsgId)
                                            }
                                        } else {
                                            Modifier.pointerInput(item.content) {
                                                detectTapGestures(
                                                    onLongPress = {
                                                        debugOnlyCopyToClipboard(
                                                            context,
                                                            item.content
                                                        )
                                                    }
                                                )
                                            }
                                        }
                                    )
                        ) {
                            if (item.content == "loading_animation" && !hasGeneratedImage) {
                                // 普通消息loading动画（非图片loading）
                                LoadingAnimation()
                            } else if (item.content == "图片生成失败" && item.localMsgId.contains(
                                    "image_error",
                                    ignoreCase = true
                                )
                            ) {
                                // 图片生成失败的错误消息：显示文本文案并可点击删除
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    Icon(
                                        painter = painterResource(R.drawable.ic_warning_voice),
                                        contentDescription = "Image generation error",
                                        tint = Color.White.copy(alpha = 0.6f),
                                        modifier = Modifier.size(16.dp),
                                    )
                                    Text(
                                        text = item.content,
                                        color = Color.White.copy(alpha = 0.6f),
                                        fontSize = 14.sp,
                                    )
                                }
                            } else if (item.content.isNotEmpty()) {
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
                        Spacer(
                            modifier = Modifier
                                .widthIn(80.dp)
                                .weight(1f)
                        )
                    }

                    // 右下角按钮（image generate）
                    // keep talking按钮已移至ChatInput右上角悬浮
                    // 如果有图片，隐藏所有按钮；否则仅在最后一条消息时显示
                    if (!isImageOnlyMessage && !hasGeneratedImage && isLatestMessage) {
                        MessageCornerActions(
                            message = item,
                            onImageGenerate = {
                                viewModel.generateImageForMessage(item.id)
                            },
                            modifier = Modifier
                                .align(Alignment.BottomEnd)
                                .padding(end = 5.dp, bottom = 5.dp)
                        )
                    }
                }
            }

            // 底部操作栏（like, dislike, recall）
            // 如果有图片，隐藏所有按钮；否则仅在最后一条消息时显示
            if (!isImageOnlyMessage && !hasGeneratedImage && isLatestMessage) {
                Spacer(modifier = Modifier.height(2.dp))
                MessageActionBar(
                    message = item,
                    onLike = {
                        viewModel.likeMessage(item.localMsgId)
                    },
                    onDislike = {
                        viewModel.dislikeMessage(item.localMsgId)
                    },
                    onRecall = {
                        viewModel.recallMessage()
                    },
                )
            }

            // 生成的图片显示（在MessageActionBar下面）
            // 包括两种情况：
            // 1. 有generatedImage（图片消息）
            // 2. 图片loading状态（content为"loading_animation"且localMsgId包含"loading_image"）
            if (hasGeneratedImage || isImageLoading) {
                Spacer(modifier = Modifier.height(8.dp))

                // 对于loading状态，使用默认尺寸；对于有generatedImage的消息，使用实际尺寸
                val imageWidth = if (isImageLoading) 300 else (item.getGeneratedImageWidth() ?: 300)
                val imageHeight =
                    if (isImageLoading) 300 else (item.getGeneratedImageHeight() ?: 300)
                val aspectRatio =
                    if (imageHeight > 0) imageWidth.toFloat() / imageHeight.toFloat() else 1f

                // 使用固定的dp宽度（1/3屏幕宽度约120dp）
                val targetWidth = 360 // 约等于1/3屏幕宽度的像素值（假设360dp屏幕）

                Box(
                    modifier = Modifier
                        .fillMaxWidth(),
                    contentAlignment = Alignment.CenterStart,
                ) {
                    if (isImageLoading) {
                        // Loading状态：显示shimmer占位，内部有loading点点点效果
                        ShimmerPlaceholder(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio),
                            cornerRadius = 12.dp,
                            showLoadingDots = true, // 显示loading点点点
                        )
                    } else if (imageLoadError || (isImageLoading && generatedImageUrl.isNullOrEmpty())) {
                        // 错误状态：显示错误文案并可点击删除
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio)
                                .clip(RoundedCornerShape(12.dp))
                                .background(Color.Black.copy(alpha = 0.3f))
                                .padding(16.dp)
                                .noRippleClickable {
                                    // 点击删除图片生成失败的消息
                                    viewModel.deleteMessage(item.localMsgId)
                                },
                            contentAlignment = Alignment.Center,
                        ) {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center,
                            ) {
                                Icon(
                                    painter = painterResource(R.drawable.ic_warning_voice),
                                    contentDescription = "Image load error",
                                    tint = Color.White.copy(alpha = 0.6f),
                                    modifier = Modifier.size(24.dp),
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "图片生成失败，点击删除",
                                    color = Color.White.copy(alpha = 0.6f),
                                    fontSize = 12.sp,
                                )
                            }
                        }
                    } else if (generatedImageUrl != null && generatedImageUrl.isNotEmpty()) {
                        // 正常显示图片
                        AsyncImage(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio)
                                .clip(RoundedCornerShape(12.dp))
                                .pointerInput(Unit) {
                                    detectTapGestures(
                                        onTap = {
                                            // 点击图片全屏查看
                                            showFullScreenImage = true
                                        }
                                    )
                                },
                            model = ImageRequest.Builder(LocalContext.current)
                                .data(
                                    getCdnImageUrl(
                                        generatedImageUrl,
                                        width = targetWidth,
                                        quality = 70
                                    )
                                )
                                .build(),
                            contentDescription = "Generated image",
                            contentScale = ContentScale.Fit,
                            alignment = Alignment.CenterStart,
                            onError = {
                                imageLoadError = true
                            },
                        )
                    } else if (generatedImageUrl.isNullOrEmpty()) {
                        // 有generatedImage但imageUrl为空，显示loading
                        ShimmerPlaceholder(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio),
                            cornerRadius = 12.dp,
                        )
                    }
                }

                // 全屏图片查看器
                if (showFullScreenImage && generatedImageUrl != null && !imageLoadError) {
                    Dialog(
                        onDismissRequest = { showFullScreenImage = false },
                        properties = DialogProperties(
                            usePlatformDefaultWidth = false,
                            dismissOnBackPress = true,
                            dismissOnClickOutside = true,
                        ),
                    ) {
                        FullScreenImageViewer(
                            imageUrl = generatedImageUrl,
                            onDismiss = { showFullScreenImage = false },
                        )
                    }
                }
            }
        }
    }.onFailure { e ->
        // 渲染失败时显示简化版本
        Row {
            val context = LocalContext.current
            Box(
                modifier =
                    Modifier
                        .background(
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
            Spacer(
                modifier = Modifier
                    .widthIn(80.dp)
                    .weight(1f)
            )
        }
    }
}

/** 用户消息显示组件 */
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
                modifier =
                    Modifier
                        .background(
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
    }.onFailure { e ->
        // 渲染失败时显示简化版本
        Row {
            Spacer(
                modifier = Modifier
                    .widthIn(80.dp)
                    .weight(1f)
            )
            val context = LocalContext.current
            Box(
                modifier =
                    Modifier
                        .background(
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
                    Modifier
                        .size(6.dp)
                        .background(color = Color.White.copy(dotAlpha * 0.7f), shape = CircleShape)
            )
        }
    }
}

/** 优化的可折叠文本卡片组件 使用新的ExpandableText组件实现 */
@Composable
internal fun AgentInfoChatCard(info: String) {

    val str = buildAnnotatedString {
        withStyle(style = SpanStyle(fontWeight = FontWeight.SemiBold)) { append("Intro: ") }
        append(info)
    }

    // 紫色渐变边框颜色（根据 Figma 设计稿 #842ba7）
    // 使用从左到右的渐变效果，从深紫到稍浅的紫色
    val purpleStart = Color(0xFF842BA7) // 主紫色 #842ba7
    val purpleEnd = Color(0xFF360B43) // 稍浅的紫色，形成渐变效果

    Box(
        modifier =
            Modifier
                .border(
                    width = .5.dp,
                    brush = Brush.horizontalGradient(
                        colors = listOf(purpleStart, purpleEnd),
                    ),
                    shape = RoundedCornerShape(12.dp),
                )
                .background(Color(0x99000000), RoundedCornerShape(12.dp)) // 背景色 rgba(0,0,0,0.6)
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
            modifier = Modifier
                .fillMaxWidth()
                .padding(end = pd.dp),
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
                    Modifier
                        .size(18.dp)
                        .align(Alignment.BottomEnd)
                        .noRippleClickable(onClick = { isExpanded = isExpanded.not() }),
                tint = Color.White,
            )
        }
    }
}
