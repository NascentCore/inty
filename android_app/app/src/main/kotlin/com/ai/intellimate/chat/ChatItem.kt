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
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.res.stringResource
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

private fun debugOnlyCopyToClipboard(context: Context, text: String) {
    val clipboard = context.getSystemService<ClipboardManager>()
    val clip = ClipData.newPlainText("Message", text)
    clipboard?.setPrimaryClip(clip)
}

@Composable
fun ChatItem(
    item: MsgInfo,
    isCurrentPage: Boolean = true,
    chatViewModel: ChatViewModel? = null,
    isLatestMessage: Boolean = false,
) {
    runCatching {
        when (item.role) {
            "assistant" -> {
                ChatItemAI(item, isCurrentPage, chatViewModel, isLatestMessage)
            }

            "user" -> {
                ChatItemUser(item)
            }

            "system" -> {
                ChatItemSystemTips(item, chatViewModel)
            }

            else -> {
                LogUtils.w("ChatItem - 未知角色: ${item.role}")
                ChatItemUser(item)
            }
        }
    }
        .onFailure { e ->
            LogUtils.e("ChatItem - 渲染失败: ${e.message}")
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

@Composable
private fun ChatItemAI(
    item: MsgInfo,
    isCurrentPage: Boolean = true,
    chatViewModel: ChatViewModel? = null,
    isLatestMessage: Boolean = false,
) {
    val viewModel = chatViewModel ?: viewModel<ChatViewModel>()

    runCatching {
        Column(modifier = Modifier.fillMaxWidth(.9f)) {
            val hasGeneratedImage = item.hasGeneratedImage()
            val generatedImageUrl = item.getGeneratedImageUrl()
            val isImageLoading = (item.content == "loading_animation" &&
                    item.localMsgId.contains("loading_image", ignoreCase = true)) ||
                    (generatedImageUrl == "loading")

            if (item.content.isNotEmpty() && item.content != "loading_animation") {
                val agentInfo by viewModel.agentInfo.collectAsState()

                val vmAgentId = agentInfo?.id
                val metaAgentId = item.agentId()
                val safeAgentId = vmAgentId ?: metaAgentId ?: ""

                val audioInfo =
                    AudioInfo(
                        url = item.audio_url ?: "",
                        title = "Voice Message",
                        artist = "AI Agent",
                        messageId = item.localMsgId,
                        agentId = safeAgentId,
                        agentName = agentInfo?.name,
                    )

                val isQueryMsgsCompleted by viewModel.isQueryMsgsCompleted.collectAsState()

                val allMessages by viewModel.msgs.collectAsState()
                val actualChatMessages =
                    allMessages.filter { !it.isOpening() && it.role != "system" }
                val isOnlyOpeningMessage = actualChatMessages.isEmpty()

                val hasPlayedOpening = OpeningPlayState.agentOpeningPlayed(agentInfo?.id ?: "")

                val shouldAutoPlay =
                    item.isOpening() &&
                            isOnlyOpeningMessage &&
                            !hasPlayedOpening &&
                            isCurrentPage &&
                            isQueryMsgsCompleted &&
                            safeAgentId.isNotEmpty() &&
                            audioInfo.url.isNotEmpty() &&
                            IntySetting.isAutoPlayAudio()

                if (safeAgentId.isNotEmpty()) {
                    VoicePlayer(
                        audioInfo = audioInfo,
                        autoPlay = shouldAutoPlay,
                        modifier = Modifier.widthIn(38.dp),
                        onTtsGenerated = { audioUrl ->
                            viewModel.updateMessageAudioUrl(item.localMsgId, audioUrl)
                        },
                        serverMessageId = item.id,
                    )
                }
            }
            val msgShape =
                if (item.content.isNotEmpty() && item.content != "loading_animation")
                    RoundedCornerShape(topEnd = 12.dp, bottomStart = 12.dp, bottomEnd = 12.dp)
                else RoundedCornerShape(12.dp)

            val isImageOnlyMessage =
                item.content.isEmpty() && hasGeneratedImage && generatedImageUrl != "loading"

            var showFullScreenImage by remember { mutableStateOf(false) }
            var imageLoadError by remember { mutableStateOf(false) }

            val isNormalLoading = item.content == "loading_animation" &&
                    !hasGeneratedImage &&
                    generatedImageUrl != "loading"

            val shouldHideText = isImageOnlyMessage || isNormalLoading

            if (isNormalLoading) {
                Box(
                    modifier =
                        Modifier
                            .background(Color.Black.copy(alpha = 0.5f), msgShape)
                            .padding(12.dp, 13.dp)
                            .widthIn(1.dp, 300.dp)
                ) {
                    LoadingAnimation()
                }
            } else if (!shouldHideText && item.content.isNotEmpty()) {
                Row(modifier = Modifier.fillMaxWidth()) {
                    val context = LocalContext.current
                    Box(
                        modifier =
                            Modifier
                                .background(Color.Black.copy(alpha = 0.5f), msgShape)
                                .padding(12.dp, 13.dp)
                                .widthIn(1.dp, 300.dp)
                                .pointerInput(item.content) {
                                    detectTapGestures(
                                        onLongPress = {
                                            debugOnlyCopyToClipboard(
                                                context,
                                                item.content
                                            )
                                        }
                                    )
                                }
                    ) {
                        if (item.content.isNotEmpty()) {
                            StyledMessageText(
                                text = item.content,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Normal,
                                normalColor = Color.White,
                                actionColor = Color.White.copy(0.55f),
                            )
                        }

                        if (!hasGeneratedImage && isLatestMessage) {
                            MessageCornerActions(
                                onImageGenerate = {
                                    viewModel.generateImageForMessage(item.id)
                                },
                                modifier = Modifier
                                    .align(Alignment.BottomEnd)
                                    .offset(10.dp, 10.dp)
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

            if (!hasGeneratedImage && isLatestMessage) {
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

            if (hasGeneratedImage || isImageLoading) {
                Spacer(modifier = Modifier.height(8.dp))

                val imageWidth = if (isImageLoading) 300 else (item.getGeneratedImageWidth() ?: 300)
                val imageHeight =
                    if (isImageLoading) 300 else (item.getGeneratedImageHeight() ?: 300)
                val aspectRatio =
                    if (imageHeight > 0) imageWidth.toFloat() / imageHeight.toFloat() else 1f

                val targetWidth = 360

                Box(
                    modifier = Modifier
                        .fillMaxWidth(),
                    contentAlignment = Alignment.CenterStart,
                ) {
                    if (isImageLoading) {
                        ShimmerPlaceholder(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio),
                            cornerRadius = 12.dp,
                            showLoadingDots = true,
                        )
                    } else if (imageLoadError) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio)
                                .clip(RoundedCornerShape(12.dp))
                                .background(Color.Black.copy(alpha = 0.3f))
                                .padding(16.dp)
                                .noRippleClickable {
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
                                    text = stringResource(R.string.image_generation_failed_tap_to_delete),
                                    color = Color.White.copy(alpha = 0.6f),
                                    fontSize = 12.sp,
                                )
                            }
                        }
                    } else if (!generatedImageUrl.isNullOrEmpty()) {
                        AsyncImage(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio)
                                .clip(RoundedCornerShape(12.dp))
                                .pointerInput(Unit) {
                                    detectTapGestures(
                                        onTap = {
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
                                ).build(),
                            contentDescription = "Generated image",
                            contentScale = ContentScale.Fit,
                            alignment = Alignment.CenterStart,
                            onError = {
                                imageLoadError = true
                            },
                        )
                    } else if (generatedImageUrl.isNullOrEmpty()) {
                        ShimmerPlaceholder(
                            modifier = Modifier
                                .fillMaxWidth(0.35f)
                                .aspectRatio(aspectRatio),
                            cornerRadius = 12.dp,
                        )
                    }
                }

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

@Composable
private fun ChatItemSystemTips(
    item: MsgInfo,
    chatViewModel: ChatViewModel? = null,
) {
    val viewModel = chatViewModel ?: viewModel<ChatViewModel>()

    val displayText = if (item.content == "image_generation_error_tip") {
        stringResource(R.string.image_generation_error_tip)
    } else {
        item.content
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            modifier = Modifier.noRippleClickable {
                viewModel.deleteMessage(item.localMsgId)
            },
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = displayText,
                color = Color.White.copy(alpha = 0.7f),
                fontSize = 10.sp,
            )
            Spacer(modifier = Modifier.width(8.dp))
            Icon(
                painter = painterResource(ai.sxwl.android.design.R.drawable.ic_delete),
                contentDescription = "Delete tip",
                tint = Color.White.copy(alpha = 0.5f),
                modifier = Modifier.size(16.dp),
            )
        }
    }
}

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
            Text(
                text = text.ifEmpty { "Message content is empty" },
                fontSize = fontSize,
                fontWeight = fontWeight,
                color = normalColor,
            )
        }
}

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

@Composable
internal fun AgentInfoChatCard(info: String) {

    val str = buildAnnotatedString {
        withStyle(style = SpanStyle(fontWeight = FontWeight.SemiBold)) { append("Intro: ") }
        append(info)
    }

    val purpleStart = Color(0xFF842BA7)
    val purpleEnd = Color(0xFF360B43)

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
                .background(Color(0x99000000), RoundedCornerShape(12.dp))
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
