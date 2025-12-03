package com.ai.intellimate.chat

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.TimeUtils
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
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
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
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.utils.ChatTextFormatter
import kotlinx.coroutines.delay

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
    isGuideVisible: Boolean = false,
    messageFontSizeSp: Float = SettingStateManager.CHAT_FONT_SIZE_DEFAULT_SP,
) {
    runCatching {
            when (item.role) {
                "assistant" -> {
                    ChatItemAI(
                        item,
                        isCurrentPage,
                        chatViewModel,
                        isLatestMessage,
                        isGuideVisible,
                        messageFontSizeSp,
                    )
                }

                "user" -> {
                    ChatItemUser(item, messageFontSizeSp)
                }

                "system" -> {
                    ChatItemSystemTips(item, chatViewModel)
                }

                else -> {
                    LogUtils.w("ChatItem - 未知角色: ${item.role}")
                    ChatItemUser(item, messageFontSizeSp)
                }
            }
        }
        .onFailure { e ->
            LogUtils.e("ChatItem - 渲染失败: ${e.message}")
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

@Composable
private fun ChatItemAI(
    item: MsgInfo,
    isCurrentPage: Boolean = true,
    chatViewModel: ChatViewModel? = null,
    isLatestMessage: Boolean = false,
    isGuideVisible: Boolean = false,
    messageFontSizeSp: Float,
) {
    val viewModel = chatViewModel ?: viewModel<ChatViewModel>()
    val timestampText = remember(item.timestamp) { formatTimestamp(item.timestamp) }
    val messageFontSize = messageFontSizeSp.sp
    val agentInfo by viewModel.agentInfo.collectAsState()

    runCatching {
            Column(modifier = Modifier.fillMaxWidth()) {
                val hasGeneratedImage = item.hasGeneratedImage()
                val generatedImageUrl = item.getGeneratedImageUrl()
                val isImageLoading =
                    (item.content == "loading_animation" &&
                        item.localMsgId.contains("loading_image", ignoreCase = true)) ||
                        (generatedImageUrl == "loading")
                val isQueryMsgsCompleted by viewModel.isQueryMsgsCompleted.collectAsState()

                if (item.content.isNotEmpty() && item.content != "loading_animation") {
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
                            IntySetting.isAutoPlayAudio() &&
                            !isGuideVisible // 未出现引导手势时

                    // 消息气泡上方的辅助内容条
                    Row(
                        modifier = Modifier.fillMaxWidth().fillMaxHeight(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        // 显示音频播放按钮
                        if (safeAgentId.isNotEmpty()) {
                            VoicePlayer(
                                audioInfo = audioInfo,
                                autoPlay = shouldAutoPlay,
                                modifier =
                                    Modifier.widthIn(UiConfigs.ChatMessagePane.AudioPlayerMinWidth),
                                onTtsGenerated = { audioUrl ->
                                    viewModel.updateMessageAudioUrl(item.localMsgId, audioUrl)
                                },
                                serverMessageId = item.id,
                            )
                        }
                        // 显示时间戳
                        if (timestampText != null) {
                            Spacer(
                                modifier =
                                    Modifier.width(
                                        UiConfigs.ChatMessagePane.AudioPlayerToTimestampSpacing
                                    )
                            )
                            ChatMessageTimestamp(
                                timestampText = timestampText,
                                fontSize = UiConfigs.ChatMessagePane.TimestampFontSize,
                            )
                        }
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

                val isNormalLoading =
                    item.content == "loading_animation" &&
                        !hasGeneratedImage &&
                        generatedImageUrl != "loading"

                val shouldHideText = isImageOnlyMessage || isNormalLoading
                val shouldFlowShow by viewModel.shouldFlowShow.collectAsState()

                if (isNormalLoading) {
                    Box(
                        modifier =
                            Modifier.background(Color.Black.copy(alpha = 0.5f), msgShape)
                                .padding(
                                    horizontal = UiConfigs.ChatMessagePane.PaddingHorizontal,
                                    vertical = UiConfigs.ChatMessagePane.PaddingVertical,
                                )
                                .widthIn(min = 1.dp)
                    ) {
                        LoadingAnimation(agentInfo?.name)
                    }
                } else if (!shouldHideText && item.content.isNotEmpty()) {
                    val allMessages by viewModel.msgs.collectAsState()
                    val agentId = agentInfo?.id ?: ""

                    // 记录查询完成时已存在的消息ID列表，用于区分历史消息和新消息
                    // 使用 LaunchedEffect 在查询完成的瞬间记录消息列表
                    // 使用 agentId 作为 key，确保切换会话时重置状态
                    var messagesAtQueryComplete by
                        remember(agentId) { mutableStateOf<Set<String>>(emptySet()) }

                    LaunchedEffect(isQueryMsgsCompleted, agentId) {
                        if (isQueryMsgsCompleted) {
                            if (messagesAtQueryComplete.isEmpty()) {
                                // 查询完成的瞬间，记录当前所有消息的ID
                                // 优先使用服务器ID，如果没有则使用localMsgId
                                messagesAtQueryComplete =
                                    allMessages
                                        .mapNotNull {
                                            it.id.takeIf { id -> id.isNotEmpty() } ?: it.localMsgId
                                        }
                                        .toSet()
                            }
                        } else {
                            // 查询未完成时，重置状态（切换会话时会触发）
                            messagesAtQueryComplete = emptySet()
                        }
                    }

                    Row(modifier = Modifier.fillMaxWidth()) {
                        val context = LocalContext.current
                        Box(
                            modifier =
                                Modifier.background(Color.Black.copy(alpha = 0.5f), msgShape)
                                    .padding(
                                        horizontal = UiConfigs.ChatMessagePane.PaddingHorizontal,
                                        vertical = UiConfigs.ChatMessagePane.PaddingVertical,
                                    )
                                    .fillMaxWidth(UiConfigs.ChatMessagePane.AI_WIDTH_RATIO)
                                    .pointerInput(item.content) {
                                        detectTapGestures(
                                            onLongPress = {
                                                debugOnlyCopyToClipboard(context, item.content)
                                            }
                                        )
                                    }
                        ) {
                            val isFlow =
                                isLatestMessage &&
                                    shouldFlowShow &&
                                    item.role == "assistant" &&
                                    item.content.isNotEmpty() &&
                                    item.content != "loading_animation"

                            if (item.content.isNotEmpty()) {
                                StyledMessageText(
                                    text = item.content,
                                    fontSize = messageFontSize,
                                    fontWeight = FontWeight.Normal,
                                    normalColor = Color.White,
                                    actionColor = Color.White.copy(0.55f),
                                    isFlow = isFlow,
                                    onDisplayComplete = {
                                        // 标记消息已完整显示，避免再次流式显示
                                        viewModel.newMsgFlowFinish()
                                    },
                                )
                            }

                            if (!hasGeneratedImage && isLatestMessage && !shouldFlowShow) {
                                MessageCornerActions(
                                    onImageGenerate = {
                                        viewModel.generateImageForMessage(item.id)
                                    },
                                    modifier =
                                        Modifier.align(Alignment.BottomEnd).offset(10.dp, 10.dp),
                                )
                            }
                        }
                        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
                    }
                }

                if (!hasGeneratedImage && isLatestMessage && !shouldFlowShow) {
                    Spacer(modifier = Modifier.height(2.dp))
                    MessageActionBar(
                        message = item,
                        onLike = { viewModel.likeMessage(item.localMsgId) },
                        onDislike = { viewModel.dislikeMessage(item.localMsgId) },
                        onRecall = { viewModel.recallMessage() },
                    )
                }

                if (hasGeneratedImage || isImageLoading) {
                    Spacer(modifier = Modifier.height(8.dp))

                    // 获取图片尺寸，loading时也会从item中获取（已设置为9:16比例）
                    val imageWidth = item.getGeneratedImageWidth() ?: 300
                    val imageHeight = item.getGeneratedImageHeight() ?: 533 // 默认9:16比例
                    val aspectRatio =
                        if (imageHeight > 0) imageWidth.toFloat() / imageHeight.toFloat()
                        else (9f / 16f)

                    val targetWidth = 360

                    Box(
                        modifier = Modifier.fillMaxWidth(),
                        contentAlignment = Alignment.CenterStart,
                    ) {
                        if (isImageLoading) {
                            ShimmerPlaceholder(
                                modifier = Modifier.fillMaxWidth(0.35f).aspectRatio(aspectRatio),
                                cornerRadius = 12.dp,
                                showLoadingDots = true,
                            )
                        } else if (imageLoadError) {
                            Box(
                                modifier =
                                    Modifier.fillMaxWidth(0.35f)
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
                                        text =
                                            stringResource(
                                                R.string.image_generation_failed_tap_to_delete
                                            ),
                                        color = Color.White.copy(alpha = 0.6f),
                                        fontSize = 12.sp,
                                    )
                                }
                            }
                        } else if (!generatedImageUrl.isNullOrEmpty()) {
                            AsyncImage(
                                modifier =
                                    Modifier.fillMaxWidth(0.35f)
                                        .aspectRatio(aspectRatio)
                                        .clip(RoundedCornerShape(12.dp))
                                        .pointerInput(Unit) {
                                            detectTapGestures(
                                                onTap = { showFullScreenImage = true }
                                            )
                                        },
                                model =
                                    ImageRequest.Builder(LocalContext.current)
                                        .data(
                                            getCdnImageUrl(
                                                generatedImageUrl,
                                                width = targetWidth,
                                                quality = 70,
                                            )
                                        )
                                        .build(),
                                contentDescription = "Generated image",
                                contentScale = ContentScale.Fit,
                                alignment = Alignment.CenterStart,
                                onError = { imageLoadError = true },
                            )
                        } else if (generatedImageUrl.isNullOrEmpty()) {
                            ShimmerPlaceholder(
                                modifier = Modifier.fillMaxWidth(0.35f).aspectRatio(aspectRatio),
                                cornerRadius = 12.dp,
                            )
                        }
                    }

                    if (showFullScreenImage && generatedImageUrl != null && !imageLoadError) {
                        Dialog(
                            onDismissRequest = { showFullScreenImage = false },
                            properties =
                                DialogProperties(
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
        }
        .onFailure { e ->
            Row {
                val context = LocalContext.current
                Box(
                    modifier =
                        Modifier.background(
                                Color.Black.copy(alpha = 0.5f),
                                RoundedCornerShape(12.dp),
                            )
                            .padding(12.dp, 13.dp)
                            .fillMaxWidth(UiConfigs.ChatMessagePane.AI_WIDTH_RATIO)
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
                        fontSize = messageFontSize,
                    )
                }
                Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
            }
        }
}

/** 用户消息气泡布局，靠右对齐。 */
@Composable
private fun ChatItemUser(item: MsgInfo, messageFontSizeSp: Float) {
    val messageFontSize = messageFontSizeSp.sp
    runCatching {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                val context = LocalContext.current
                Box(
                    modifier =
                        Modifier.background(
                                Color.White.copy(alpha = 0.6f),
                                RoundedCornerShape(12.dp),
                            )
                            .padding(
                                horizontal = UiConfigs.ChatMessagePane.PaddingHorizontal,
                                vertical = UiConfigs.ChatMessagePane.PaddingVertical,
                            )
                            .widthIn(
                                min = 1.dp,
                                max = UiConfigs.ChatMessagePane.UserMessageMaxWidth,
                            )
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
                        fontSize = messageFontSize,
                        fontWeight = FontWeight.Normal,
                        normalColor = Color(0xff090909),
                        actionColor = Color(0xff090909).copy(0.6f),
                    )
                }
            }
        }
        // 如果渲染失败，显示空消息气泡；应无可能发生，仅作为保守的兜底处理。
        .onFailure { e ->
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                val context = LocalContext.current
                Box(
                    modifier =
                        Modifier.background(
                                Color.White.copy(alpha = 0.6f),
                                RoundedCornerShape(12.dp),
                            )
                            .padding(
                                horizontal = UiConfigs.ChatMessagePane.PaddingHorizontal,
                                vertical = UiConfigs.ChatMessagePane.PaddingVertical,
                            )
                            .widthIn(
                                min = 1.dp,
                                max = UiConfigs.ChatMessagePane.UserMessageMaxWidth,
                            )
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
                        fontSize = messageFontSize,
                    )
                }
            }
        }
}

@Composable
private fun ChatItemSystemTips(item: MsgInfo, chatViewModel: ChatViewModel? = null) {
    val viewModel = chatViewModel ?: viewModel<ChatViewModel>()

    val displayText =
        if (item.content == "image_generation_error_tip") {
            stringResource(R.string.image_generation_error_tip)
        } else {
            item.content
        }

    Box(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Row(
            modifier = Modifier.noRippleClickable { viewModel.deleteMessage(item.localMsgId) },
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(text = displayText, color = Color.White.copy(alpha = 0.7f), fontSize = 10.sp)
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
    isFlow: Boolean = false,
    onDisplayComplete: (() -> Unit)? = null,
) {

    // 构建当前显示的文本
    val displayedText =
        if (isFlow) {
            // 将文本分割为单词（保留空格和标点）
            val words = remember(text) { splitIntoWords(text) }

            // 当前显示的单词数量
            var displayedWordCount by remember(text) { mutableIntStateOf(0) }
            val displayCompleteCall by rememberUpdatedState(onDisplayComplete)

            // 流式显示逻辑
            LaunchedEffect(text) {
                displayedWordCount = 0
                words.forEachIndexed { index, _ ->
                    delay(50) // 每个单词延迟50ms
                    displayedWordCount = index + 1
                }
                // 所有单词显示完成后，调用回调
                displayCompleteCall?.invoke()
            }

            /*DisposableEffect(Unit) {
                onDispose { displayCompleteCall?.invoke() }
            }*/

            remember(displayedWordCount, words, text) {
                val partialText = words.take(displayedWordCount).joinToString("")
                // 检查并补完括号，确保括号始终完整
                ensureBracketsComplete(partialText, text)
            }
        } else {
            text
        }

    Text(
        text =
            ChatTextFormatter.formatChatMessage(
                text = displayedText,
                fontSize = fontSize,
                fontWeight = fontWeight,
                normalColor = normalColor,
                italicColor = actionColor,
            )
    )
}

/**
 * 将文本分割为单词，保留空格和标点符号 使用正则表达式按单词边界分割，保留空格 例如："Hello (world) test" -> ["Hello ", "(world) ", "test"]
 */
private fun splitIntoWords(text: String): List<String> {
    if (text.isEmpty()) return emptyList()

    val words = mutableListOf<String>()
    // 使用正则表达式匹配：非空白字符序列（单词，包括括号、标点等）和后续的空白字符
    val pattern = Regex("""\S+\s*""")
    var lastIndex = 0

    pattern.findAll(text).forEach { matchResult ->
        // 如果匹配结果之前有未匹配的字符（如开头的空格），先添加它们
        if (matchResult.range.first > lastIndex) {
            words.add(text.substring(lastIndex, matchResult.range.first))
        }
        words.add(matchResult.value)
        lastIndex = matchResult.range.last + 1
    }

    // 添加剩余的文本（如末尾的空格）
    if (lastIndex < text.length) {
        words.add(text.substring(lastIndex))
    }

    // 如果正则没有匹配到任何内容，返回原文本
    if (words.isEmpty()) {
        return listOf(text)
    }

    return words
}

/**
 * 确保括号完整：检查部分文本中的括号是否完整，如果不完整则补完
 *
 * @param partialText 部分显示的文本
 * @param fullText 完整文本
 * @return 补完括号后的文本
 */
private fun ensureBracketsComplete(partialText: String, fullText: String): String {
    if (partialText.isEmpty() || partialText.length >= fullText.length) {
        return partialText
    }

    val bracketPairs = findBracketPairs(fullText)
    if (bracketPairs.isEmpty()) {
        return partialText
    }

    val result = StringBuilder(partialText)
    val pendingClosures =
        bracketPairs
            .asSequence()
            .filter { (start, end) -> start < partialText.length && end >= partialText.length }
            .sortedByDescending { it.first } // 先关闭内层，再关闭外层
            .toList()

    pendingClosures.forEach { (_, end) ->
        val bracketEndChar = fullText[end]
        val afterBracket = end + 1
        val trailingSpace =
            if (afterBracket < fullText.length && fullText[afterBracket].isWhitespace()) {
                var spaceEnd = afterBracket
                while (spaceEnd < fullText.length && fullText[spaceEnd].isWhitespace()) {
                    spaceEnd++
                }
                fullText.substring(afterBracket, spaceEnd)
            } else {
                ""
            }

        result.append(bracketEndChar).append(trailingSpace)
    }

    return result.toString()
}

/** 查找匹配的括号对（包括中英文括号） 复用 ChatTextFormatter 的逻辑 */
private fun findBracketPairs(text: String): List<Pair<Int, Int>> {
    val bracketPairs = mutableListOf<Pair<Int, Int>>()
    val stack = mutableListOf<Pair<Char, Int>>()

    text.forEachIndexed { index, char ->
        when (char) {
            '(',
            '（' -> stack.add(Pair(char, index))
            ')',
            '）' -> {
                val matchingStart = if (char == ')') '(' else '（'
                for (i in stack.size - 1 downTo 0) {
                    if (stack[i].first == matchingStart) {
                        bracketPairs.add(Pair(stack[i].second, index))
                        stack.removeAt(i)
                        break
                    }
                }
            }
        }
    }

    return bracketPairs.sortedBy { it.first }
}

@Composable
private fun LoadingAnimation(agentName: String?) {
    val infiniteTransition = rememberInfiniteTransition(label = "loading")
    val fallbackName =
        agentName?.takeIf { it.isNotBlank() }
            ?: stringResource(R.string.chat_ai_typing_default_name)
    val typingPlaceholder = stringResource(R.string.chat_ai_typing_placeholder, fallbackName)

    Row(
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text = typingPlaceholder, color = Color.White.copy(alpha = 0.7f), fontSize = 12.sp)
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
                        animationSpec =
                            infiniteRepeatable(animation = tween(600, delayMillis = delay)),
                        label = "dot_alpha_$index",
                    )

                Box(
                    modifier =
                        Modifier.size(6.dp)
                            .background(
                                color = Color.White.copy(dotAlpha * 0.7f),
                                shape = CircleShape,
                            )
                )
            }
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
            Modifier.border(
                    width = .5.dp,
                    brush = Brush.horizontalGradient(colors = listOf(purpleStart, purpleEnd)),
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
            modifier = Modifier.fillMaxWidth().padding(end = pd.dp),
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
                    Modifier.size(18.dp)
                        .align(Alignment.BottomEnd)
                        .noRippleClickable(onClick = { isExpanded = isExpanded.not() }),
                tint = Color.White,
            )
        }
    }
}

@Composable
private fun ChatMessageTimestamp(timestampText: String?, fontSize: TextUnit) {
    if (timestampText.isNullOrEmpty()) {
        return
    }

    Text(
        text = timestampText,
        color = Color.White.copy(alpha = 0.55f),
        fontSize = fontSize,
        // 保证行高与字体大小一致，保证居中对齐有效
        lineHeight = fontSize,
    )
}

private fun formatTimestamp(rawTimestamp: String?): String? {
    if (rawTimestamp.isNullOrBlank()) return null
    return TimeUtils.convertUtcToLocalFull(rawTimestamp).takeIf { it.isNotBlank() }
}
