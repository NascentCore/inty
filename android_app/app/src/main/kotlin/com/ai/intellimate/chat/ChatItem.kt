package com.ai.intellimate.chat

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.data.store.VoiceCallRecordingEntry
import ai.sxwl.android.data.store.VoiceCallRecordingIndex
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.firebase.logEvent
import ai.sxwl.android.utils.TimeUtils
import ai.sxwl.android.utils.ToastUtils
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.KeyboardArrowUp
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.constraintlayout.compose.ConstraintLayout
import androidx.core.content.getSystemService
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.R
import com.ai.intellimate.agent.heartbeat.toHeartbeat
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
import com.ai.intellimate.xb.navigation.Routes
import java.io.File
import kotlin.time.Duration.Companion.seconds
import kotlinx.coroutines.delay

private fun debugOnlyCopyToClipboard(context: Context, text: String) {
    val clipboard = context.getSystemService<ClipboardManager>()
    val clip = ClipData.newPlainText("Message", text)
    clipboard?.setPrimaryClip(clip)
}

private const val DEBUG_METADATA_VALUE_MAX = 64

@Composable
fun ChatItem(
    navController: NavController,
    isOnlyOpeningMessage: Boolean,
    item: MessageEntity,
    agentName: String? = null,
    isCurrentPage: Boolean = true,
    chatViewModel: ChatViewModel? = null,
    voiceCallRecordingIndex: VoiceCallRecordingIndex = VoiceCallRecordingIndex.empty(),
    isLatestMessage: Boolean = false,
    isGuideVisible: Boolean = false,
    messageFontSizeSp: Float = SettingStateManager.CHAT_FONT_SIZE_DEFAULT_SP,
) {

    if (item.type == "text" || item.type.isNullOrBlank()) {
        when (item.role) {
            "assistant" -> {
                ChatItemAI(
                    navController,
                    isOnlyOpeningMessage = isOnlyOpeningMessage,
                    item,
                    isCurrentPage,
                    chatViewModel,
                    voiceCallRecordingIndex,
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
                ChatItemVersionSupport()
            }
        }
    } else {
        when (item.type) {
            "festival_memory_prompt" ->
                ChatItemFestivalMemory(
                    agentName = agentName.orEmpty(),
                    onClick = {
                        FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                            "click_type" to "heartbeat",
                            "agent_id" to item.metaData.agentId,
                            "memory_id" to item.festivalMemoryId,
                        )
                        navController.toHeartbeat(
                            item.metaData.agentId,
                            item.festivalMemoryId,
                            "message_notify",
                        )
                    },
                )
            else -> {
                ChatItemVersionSupport()
            }
        }
    }
}

private val itemDefaultBackgroundColor = Color.Black.copy(0.5f)

@Composable
private fun ChatItem(
    modifier: Modifier = Modifier,
    color: Color = itemDefaultBackgroundColor,
    contentColor: Color = Color.White,
    content: @Composable BoxScope.() -> Unit,
) {
    Surface(
        modifier = modifier.padding(bottom = 16.dp),
        shape = MaterialTheme.shapes.medium,
        color = color,
        contentColor = contentColor,
    ) {
        Box(Modifier.padding(16.dp), content = content)
    }
}

@Composable
private fun ChatItemVersionSupport(modifier: Modifier = Modifier) {
    ChatItem(modifier = modifier) {
        Text(
            text = stringResource(R.string.chat_message_type_unsupported),
            modifier = Modifier.alpha(0.8f),
        )
    }
}

@Preview
@Composable
private fun VersionSupportPreview() {
    IntelliMateTheme { ChatItemVersionSupport() }
}

@Composable
private fun ChatItemFestivalMemory(
    agentName: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {

    ChatItem(
        modifier = modifier,
        color = MaterialTheme.colorScheme.primary.copy(alpha = .5f),
        contentColor = MaterialTheme.colorScheme.onPrimary,
    ) {
        Text(
            text =
                buildAnnotatedString {
                    append(stringResource(R.string.chat_festival_memory_notify, agentName))
                    append(stringResource(R.string.take_a_look))
                },
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().noRippleClickable(onClick = onClick),
        )
    }
}

@Preview
@Composable
private fun FestivalMemoryPreview() {
    IntelliMateTheme { ChatItemFestivalMemory(agentName = "Agent", onClick = {}) }
}

@Composable
private fun ChatItemAI(
    navController: NavController,
    isOnlyOpeningMessage: Boolean,
    item: MessageEntity,
    isCurrentPage: Boolean = true,
    chatViewModel: ChatViewModel? = null,
    voiceCallRecordingIndex: VoiceCallRecordingIndex = VoiceCallRecordingIndex.empty(),
    isLatestMessage: Boolean = false,
    isGuideVisible: Boolean = false,
    messageFontSizeSp: Float,
) {
    val viewModel = chatViewModel ?: viewModel<ChatViewModel>()
    val timestampText = remember(item.timestamp) { formatTimestamp(item.timestamp) }
    val messageFontSize = messageFontSizeSp.sp
    val agentInfo by viewModel.agentInfo.collectAsState()

    runCatching {
            Column(modifier = Modifier.padding(bottom = 16.dp).fillMaxWidth()) {
                val hasGeneratedImage = item.hasGeneratedImage()
                val generatedImageUrl = item.getGeneratedImageUrl()
                val isImageLoading = generatedImageUrl == "loading"
                val autoPlayAudioSetting by
                    SettingStateManager.autoPlayAudioFlow.collectAsState(false)

                if (item.content.isNotEmpty() && item.content != "loading_animation") {
                    val vmAgentId = agentInfo?.id
                    val metaAgentId = item.agentId()
                    val safeAgentId = vmAgentId ?: metaAgentId ?: ""
                    val localVoiceRecordingUrl =
                        remember(item, voiceCallRecordingIndex) {
                            resolveLocalVoiceRecordingUrl(
                                item = item,
                                voiceCallRecordingIndex = voiceCallRecordingIndex,
                            )
                        }
                    val preferredAudioUrl = localVoiceRecordingUrl ?: item.audioUrl.orEmpty()

                    val audioInfo =
                        AudioInfo(
                            url = preferredAudioUrl,
                            title = "Voice Message",
                            artist = "AI Agent",
                            messageId = item.id.takeIf { it.isNotBlank() },
                            agentId = safeAgentId,
                            agentName = agentInfo?.name,
                        )

                    val hasPlayedOpening = OpeningPlayState.agentOpeningPlayed(agentInfo?.id ?: "")

                    val shouldAutoPlay =
                        item.isOpening &&
                            isOnlyOpeningMessage &&
                            !hasPlayedOpening &&
                            isCurrentPage &&
                            safeAgentId.isNotEmpty() &&
                            audioInfo.url.isNotEmpty() &&
                            autoPlayAudioSetting &&
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
                                    viewModel.updateMessageAudioUrl(item.id, audioUrl)
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
                // 使用 generatedImageUrl 作为 key，URL 变化时自动重置状态
                var imageLoadError by remember(generatedImageUrl) { mutableStateOf(false) }
                var imageLoadSuccess by remember(generatedImageUrl) { mutableStateOf(false) }

                val isNormalLoading =
                    item.content == "loading_animation" &&
                        !hasGeneratedImage &&
                        generatedImageUrl != "loading"

                val shouldHideText = isImageOnlyMessage || isNormalLoading
                val shouldFlowShow by viewModel.shouldFlowShow.collectAsState()
                val shouldShowMessageActions by
                    remember(isLatestMessage) {
                        derivedStateOf {
                            isLatestMessage &&
                                !shouldFlowShow &&
                                !item.isOpening &&
                                !isNormalLoading
                        }
                    }

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
                                        viewModel.generateImageForMessageOrPickImage(item.id)
                                    },
                                    modifier =
                                        Modifier.align(Alignment.BottomEnd).offset(10.dp, 10.dp),
                                )
                            }
                        }
                        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
                    }
                }

                // 无生图时，操作区跟随文字 bubble；有生图时操作区挪到图片预览下方（见后续）
                if (shouldShowMessageActions && !(hasGeneratedImage || isImageLoading)) {
                    Spacer(modifier = Modifier.height(2.dp))
                    MessageActionBar(
                        message = item,
                        onLike = { viewModel.likeMessage(item.id) },
                        onDislike = { viewModel.dislikeMessage(item.id) },
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
                            val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
                            ShimmerPlaceholder(
                                modifier = Modifier.fillMaxWidth(0.35f).aspectRatio(aspectRatio),
                                cornerRadius = 12.dp,
                                showLoadingDots = true,
                                showSpeedUpButton = !vipStatus.isSubscribed,
                                onVipSpeedUpClick = {
                                    FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                                        "click_type" to "image speed up"
                                    )
                                    navController.navigate(Routes.Me.vipCenter("speed up "))
                                },
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
                                            viewModel.clearGeneratedImage(item.id)
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
                            // 消息生图的结果图片
                            ConstraintLayout(modifier = Modifier) {
                                val (img, left, right) = createRefs()

                                // 使用 Box 叠加 shimmer 和图片
                                Box(
                                    modifier =
                                        Modifier.fillMaxWidth(0.35f)
                                            .aspectRatio(aspectRatio)
                                            .constrainAs(img) {}
                                            .clip(RoundedCornerShape(12.dp))
                                            .pointerInput(Unit) {
                                                detectTapGestures(
                                                    onTap = { showFullScreenImage = true }
                                                )
                                            }
                                ) {
                                    // 图片加载中显示 shimmer（无 dots）
                                    if (!imageLoadSuccess) {
                                        ShimmerPlaceholder(
                                            modifier = Modifier.matchParentSize(),
                                            cornerRadius = 12.dp,
                                            showLoadingDots = false,
                                        )
                                    }

                                    // AsyncImage 在后台加载，加载成功后显示
                                    AsyncImage(
                                        modifier = Modifier.matchParentSize(),
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
                                        onSuccess = { imageLoadSuccess = true },
                                    )
                                }
                            }
                        } else {
                            // URL 为空或其他情况，显示 shimmer
                            ShimmerPlaceholder(
                                modifier = Modifier.fillMaxWidth(0.35f).aspectRatio(aspectRatio),
                                cornerRadius = 12.dp,
                            )
                        }
                    }
                    // 消息生图的查看大图
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
                            val agentId = agentInfo?.id ?: ""
                            val context = LocalContext.current
                            FullScreenImageViewer(
                                imageUrl = generatedImageUrl,
                                onDismiss = { showFullScreenImage = false },
                                onAction = {
                                    if (agentId.isNotBlank() && generatedImageUrl.isNotBlank()) {
                                        IntySetting.setChatBackgroundImage(
                                            agentId,
                                            generatedImageUrl,
                                        )
                                        ToastUtils.showShort(
                                            R.string.agent_gallery_background_set_success
                                        )
                                        showFullScreenImage = false
                                    }
                                },
                                actionLabel =
                                    stringResource(R.string.agent_gallery_set_as_background),
                                onReport = {
                                    if (agentId.isNotBlank()) {
                                        navController.navigate(
                                            Routes.Me.reportPage(false, "AGENT", agentId)
                                        )
                                        //
                                        // ReportActivity.launch(
                                        //                                            context,
                                        //                                            targetType =
                                        // "AGENT",
                                        //                                            targetId =
                                        // agentId,
                                        //                                        )
                                    }
                                },
                            )
                        }
                    }
                }

                // 生图预览下方的 👍/👎（布局与文字 bubble 一致）
                // 只在生图完成后显示点赞/点踩按钮，生图过程中不显示
                if (shouldShowMessageActions && hasGeneratedImage && !isImageLoading) {
                    Spacer(modifier = Modifier.height(2.dp))
                    MessageActionBar(
                        message = item,
                        onLike = { viewModel.likeMessage(item.id) },
                        onDislike = { viewModel.dislikeMessage(item.id) },
                        onRecall = { viewModel.recallMessage() },
                    )
                }

                if (BuildConfig.DEBUG) {
                    Row(modifier = Modifier.fillMaxWidth()) {
                        DebugMessageMetadata(
                            item = item,
                            modifier =
                                Modifier.fillMaxWidth(UiConfigs.ChatMessagePane.AI_WIDTH_RATIO),
                        )
                        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
                    }
                }
            }
        }
        .onFailure {
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
private fun ChatItemUser(item: MessageEntity, messageFontSizeSp: Float) {
    val messageFontSize = messageFontSizeSp.sp
    runCatching {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.Bottom,
            ) {
                val context = LocalContext.current

                Box(
                    modifier =
                        Modifier.background(
                                Color.White.copy(alpha = 0.6f),
                                RoundedCornerShape(12.dp),
                            )
                            .padding(
                                horizontal = UiConfigs.ChatMessagePane.PaddingHorizontal,
                                vertical = UiConfigs.ChatMessagePane.UserMessagePaddingVertical,
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
        .also {
            if (BuildConfig.DEBUG) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    DebugMessageMetadata(
                        item = item,
                        modifier =
                            Modifier.widthIn(
                                min = 1.dp,
                                max = UiConfigs.ChatMessagePane.UserMessageMaxWidth,
                            ),
                    )
                }
            }
        }
        .onFailure {
            // 如果渲染失败，显示空消息气泡；应无可能发生，仅作为保守的兜底处理。
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
                                vertical = UiConfigs.ChatMessagePane.UserMessagePaddingVertical,
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
private fun ChatItemSystemTips(item: MessageEntity, chatViewModel: ChatViewModel? = null) {
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
            modifier =
                Modifier.noRippleClickable { viewModel.deleteMessage(item.id, item.indexId) },
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
private fun DebugMessageMetadata(item: MessageEntity, modifier: Modifier = Modifier) {
    if (!BuildConfig.DEBUG) return

    val metadataLines =
        remember(item) {
                buildList {
                    val roleLabel = item.role.ifBlank { "unknown" }
                    add("role=$roleLabel")
                    item.id.takeIf { it.isNotBlank() }?.let { add("id=${it.debugEllipsize()}") }
                    add("local=${item.id}")
                    item.timestamp?.takeIf { it.isNotBlank() }?.let { add("ts=$it") }
                    item.metaData.let { meta ->
                        val metaParts = mutableListOf<String>()
                        meta.agentId.takeIf { it.isNotBlank() }?.let { metaParts += "agent=$it" }
                        if (meta.isOpening) metaParts += "opening=true"
                        meta.voiceSessionId
                            ?.takeIf { it.isNotBlank() }
                            ?.let { metaParts += "voiceSession=$it" }
                        meta.voiceTurnId
                            ?.takeIf { it.isNotBlank() }
                            ?.let { metaParts += "voiceTurn=$it" }
                        meta.generatedImage?.let { image ->
                            metaParts +=
                                "image=${image.imageUrl?.debugEllipsize()} (${image.width}x${image.height})"
                        }
                        if (metaParts.isNotEmpty()) add("meta=${metaParts.joinToString()}")
                    }
                    item.audioUrl
                        ?.takeIf { it.isNotBlank() }
                        ?.let { add("audio=${it.debugEllipsize()}") }
                    item.userVote?.let { add("vote=$it") }
                }
            }
            .filter { it.isNotBlank() }

    if (metadataLines.isEmpty()) return

    Box(
        modifier =
            modifier
                .padding(top = 4.dp)
                .background(Color.White.copy(alpha = 0.08f), RoundedCornerShape(8.dp))
                .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(
            text = metadataLines.joinToString(separator = "\n"),
            fontSize = 10.sp,
            lineHeight = 12.sp,
            color = Color(0xFF8DF0FF),
        )
    }
}

private fun String.debugEllipsize(maxLength: Int = DEBUG_METADATA_VALUE_MAX): String {
    if (maxLength !in 4..<length) {
        return this
    }
    return take(maxLength - 3) + "..."
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

            DisposableEffect(Unit) { onDispose { displayCompleteCall?.invoke() } }

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
    return TimeUtils.convertUtcToLocalFullForDisplay(rawTimestamp).takeIf { it.isNotBlank() }
}

/** 计算语音消息组的时长（秒） 通过最后一条AI语音消息的时间戳减去第一条用户消息的时间戳计算 */
private fun calculateVoiceChatDuration(messages: List<MessageEntity>): Long {
    if (messages.isEmpty()) return 0L

    // 找到第一条用户消息的时间戳
    val firstUserMessage = messages.firstOrNull { it.role == "user" }
    val firstUserTimestamp =
        firstUserMessage?.timestamp?.let { TimeUtils.parseIsoTimeToTimestamp(it) }

    // 找到最后一条AI语音消息的时间戳
    val lastAiVoiceMessage = messages.lastOrNull { it.role == "assistant" && it.isVoice }
    val lastAiVoiceTimestamp =
        lastAiVoiceMessage?.timestamp?.let { TimeUtils.parseIsoTimeToTimestamp(it) }

    // 如果缺少任一时间戳，返回0
    if (firstUserTimestamp == null || lastAiVoiceTimestamp == null) return 0L

    // 计算时长（秒）：最后一条AI语音消息 - 第一条用户消息
    val durationSeconds = (lastAiVoiceTimestamp - firstUserTimestamp) / 1000
    return durationSeconds.coerceAtLeast(0)
}

/**
 * 格式化时长为可读字符串
 *
 * @param durationSeconds 时长（秒）
 * @return
 */
private fun formatDuration(durationSeconds: Long): String {
    return durationSeconds.seconds.toString()
}

/** 从语音消息组中提取可用于关联录音文件的 session id。 */
private fun resolveVoiceSessionId(messages: List<MessageEntity>): String? {
    return messages.firstNotNullOfOrNull { msg ->
        msg.metaData.voiceSessionId?.takeIf { it.isNotBlank() }
    }
}

/** 从语音消息组中提取 turn id。 */
private fun resolveVoiceTurnId(messages: List<MessageEntity>): String? {
    return messages.firstNotNullOfOrNull { msg ->
        msg.metaData.voiceTurnId?.takeIf { it.isNotBlank() }
    }
}

private fun buildVoiceTurnKey(voiceSessionId: String, voiceTurnId: String): String {
    return VoiceCallRecordingIndex.buildTurnKey(voiceSessionId, voiceTurnId)
}

private fun resolveLocalVoiceRecordingUrl(
    item: MessageEntity,
    voiceCallRecordingIndex: VoiceCallRecordingIndex,
): String? {
    if (!item.isVoice || item.role != "assistant") return null
    val voiceSessionId = item.metaData.voiceSessionId?.trim().orEmpty()
    if (voiceSessionId.isBlank()) return null
    val voiceTurnId = item.metaData.voiceTurnId?.trim().orEmpty()
    val matched = voiceCallRecordingIndex.resolve(voiceSessionId, voiceTurnId) ?: return null
    val path = matched.recordingPath.trim()
    if (path.isBlank()) return null
    val file = File(path)
    if (!file.exists() || !file.isFile) return null
    return "file://$path"
}

/**
 * 语音通话历史卡片中的“整段录音回放”按钮。
 *
 * 使用场景：仅用于 voice call 历史折叠卡片/展开卡片头部，播放该 session 对应的本地完整录音。 预期视觉效果：复用消息中的 VoicePlayer
 * 胶囊样式，保证聊天区音频控件视觉一致。 可配置项：录音条目、sessionId 与外层 modifier。
 */
@Composable
private fun VoiceCallRecordingReplayButton(
    recording: VoiceCallRecordingEntry,
    recordingKey: String,
    modifier: Modifier = Modifier,
) {
    val recordingUri = remember(recording.recordingPath) { "file://${recording.recordingPath}" }
    val recordingLabel = stringResource(R.string.voice_chat_history_recording)
    VoicePlayer(
        audioInfo =
            AudioInfo(
                url = recordingUri,
                title = recordingLabel,
                artist = recordingLabel,
                messageId = "voice_call_recording_$recordingKey",
                agentId = recording.agentId,
            ),
        autoPlay = false,
        modifier = modifier.widthIn(UiConfigs.ChatMessagePane.AudioPlayerMinWidth),
    )
}

/**
 * 语音聊天历史记录折叠组件 显示折叠的语音聊天记录卡片，包含标题、时长、消息数量和点击提示
 *
 * 视觉效果： ┌─────────────────────────────────┐ │ Voice chat history │ │ 🎙 Duration 27s · 6 messages │
 * │ Tap to view │ └─────────────────────────────────┘
 *
 * @param messages 语音消息列表，用于计算时长和消息数量
 * @param onClick 点击展开的回调
 */
@Composable
fun VoiceChatHistoryCollapsed(
    messages: List<MessageEntity>,
    onClick: () -> Unit,
    recordingReplayKey: String?,
    recording: VoiceCallRecordingEntry? = null,
    modifier: Modifier = Modifier,
) {
    val durationSeconds = remember(messages) { calculateVoiceChatDuration(messages) }
    val durationText = remember(durationSeconds) { formatDuration(durationSeconds) }
    val messageCount = messages.size

    Box(
        modifier =
            modifier.fillMaxWidth().noRippleClickable(onClick = onClick).padding(vertical = 8.dp)
    ) {
        Row(
            modifier =
                Modifier.fillMaxWidth(UiConfigs.ChatMessagePane.AI_WIDTH_RATIO)
                    .background(
                        color = Color.Black.copy(alpha = 0.5f),
                        shape = RoundedCornerShape(12.dp),
                    )
                    .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.Start) {
                // 标题
                Text(
                    text = stringResource(R.string.voice_chat_history_title),
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(modifier = Modifier.height(4.dp))
                // 时长和消息数量
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        painter = painterResource(R.drawable.ic_mic),
                        contentDescription = null,
                        tint = Color.White.copy(alpha = 0.7f),
                        modifier = Modifier.size(14.dp),
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text =
                            stringResource(
                                R.string.voice_chat_history_duration_messages,
                                durationText,
                                messageCount,
                            ),
                        color = Color.White.copy(alpha = 0.7f),
                        fontSize = 12.sp,
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                // 点击提示
                Text(
                    text = stringResource(R.string.voice_chat_history_tap_to_view),
                    color = Color.White.copy(alpha = 0.5f),
                    fontSize = 11.sp,
                )
            }

            Column(
                horizontalAlignment = Alignment.End,
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (recording != null && !recordingReplayKey.isNullOrBlank()) {
                    VoiceCallRecordingReplayButton(
                        recording = recording,
                        recordingKey = recordingReplayKey,
                    )
                }
                Image(
                    imageVector = Icons.Rounded.KeyboardArrowDown,
                    contentDescription = null,
                    colorFilter = ColorFilter.tint(Color.White.copy(alpha = 0.7f)),
                    modifier = Modifier.size(20.dp),
                )
            }
        }
    }
}

/**
 * 语音聊天历史记录展开后的大气泡容器 将展开的语音消息内容包裹在一个半透明背景的大气泡中 顶部显示与折叠状态相同样式的卡片，但提示文字改为"Tap to collapse"
 * 内部的每条消息仍使用原有的普通消息气泡样式
 *
 * @param messages 语音消息列表，用于显示时长和消息数量
 * @param onCollapse 点击折叠的回调
 * @param content 气泡内部内容（语音消息列表的 Composable）
 */
@Composable
fun VoiceChatHistoryExpandedContainer(
    messages: List<MessageEntity>,
    onCollapse: () -> Unit,
    recordingReplayKey: String?,
    recording: VoiceCallRecordingEntry? = null,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val containerShape = RoundedCornerShape(16.dp)
    val durationSeconds = remember(messages) { calculateVoiceChatDuration(messages) }
    val durationText = remember(durationSeconds) { formatDuration(durationSeconds) }
    val messageCount = messages.size

    Column(
        modifier =
            modifier
                .padding(bottom = 16.dp)
                .fillMaxWidth()
                .background(Color.Black.copy(alpha = 0.5f), containerShape)
                .padding(12.dp)
    ) {
        // 顶部折叠提示卡片（与折叠状态相同样式，但提示文字不同）
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .noRippleClickable(onClick = onCollapse)
                    .padding(bottom = 8.dp)
        ) {
            Row(
                modifier =
                    Modifier.fillMaxWidth()
                        .background(
                            color = Color.Black.copy(alpha = 0.3f),
                            shape = RoundedCornerShape(12.dp),
                        )
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.Start) {
                    // 标题
                    Text(
                        text = stringResource(R.string.voice_chat_history_title),
                        color = Color.White,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    // 时长和消息数量
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            painter = painterResource(R.drawable.ic_mic),
                            contentDescription = null,
                            tint = Color.White.copy(alpha = 0.7f),
                            modifier = Modifier.size(14.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text =
                                stringResource(
                                    R.string.voice_chat_history_duration_messages,
                                    durationText,
                                    messageCount,
                                ),
                            color = Color.White.copy(alpha = 0.7f),
                            fontSize = 12.sp,
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    // 点击提示（展开状态显示"Tap to collapse"）
                    Text(
                        text = stringResource(R.string.voice_chat_history_tap_to_collapse),
                        color = Color.White.copy(alpha = 0.5f),
                        fontSize = 11.sp,
                    )
                }

                Column(
                    horizontalAlignment = Alignment.End,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    if (recording != null && !recordingReplayKey.isNullOrBlank()) {
                        VoiceCallRecordingReplayButton(
                            recording = recording,
                            recordingKey = recordingReplayKey,
                        )
                    }
                    // 向上箭头图标（表示可折叠）
                    Image(
                        imageVector = Icons.Rounded.KeyboardArrowUp,
                        contentDescription = null,
                        colorFilter = ColorFilter.tint(Color.White.copy(alpha = 0.7f)),
                        modifier = Modifier.size(20.dp),
                    )
                }
            }
        }

        // 消息内容
        content()
    }
}

/**
 * 语音消息组 UI：折叠时显示摘要卡片，展开时显示每条消息的气泡。 在内部维护展开/折叠状态，使用 VoiceChatHistoryCollapsed 与
 * VoiceChatHistoryExpandedContainer。
 *
 * @param messages 语音组消息列表（可为 null 的 Paging 项），会过滤掉 null 后使用
 * @param navController 用于单条消息内跳转
 * @param chatViewModel 可为 null，用于消息操作
 * @param isCurrentPage 是否当前页
 * @param isGuideVisible 是否显示引导
 * @param messageFontSizeSp 消息字号
 * @param modifier 布局修饰
 */
@Composable
fun CallMessages(
    messages: List<MessageEntity?>,
    navController: NavController,
    chatViewModel: ChatViewModel?,
    voiceCallRecordingIndex: VoiceCallRecordingIndex = VoiceCallRecordingIndex.empty(),
    onCollapseChange: () -> Unit,
    modifier: Modifier = Modifier,
    isCurrentPage: Boolean = true,
    isGuideVisible: Boolean = false,
    messageFontSizeSp: Float = SettingStateManager.CHAT_FONT_SIZE_DEFAULT_SP,
) {
    val list = remember(messages) { messages.filterNotNull() }
    val voiceSessionId = remember(list) { resolveVoiceSessionId(list) }
    val voiceTurnId = remember(list) { resolveVoiceTurnId(list) }
    val turnRecordingKey =
        remember(voiceSessionId, voiceTurnId) {
            if (voiceSessionId.isNullOrBlank() || voiceTurnId.isNullOrBlank()) null
            else buildVoiceTurnKey(voiceSessionId, voiceTurnId)
        }
    val recording =
        remember(voiceSessionId, voiceTurnId, voiceCallRecordingIndex) {
            voiceCallRecordingIndex
                .resolve(voiceSessionId = voiceSessionId, voiceTurnId = voiceTurnId)
                ?.takeIf { File(it.recordingPath).exists() }
        }
    val replayKey = remember(turnRecordingKey, voiceSessionId) { turnRecordingKey ?: voiceSessionId }
    var expanded by rememberSaveable { mutableStateOf(false) }

    if (expanded) {
        VoiceChatHistoryExpandedContainer(
            messages = list,
            onCollapse = {
                expanded = false
                onCollapseChange()
            },
            recordingReplayKey = replayKey,
            recording = recording,
            modifier = modifier,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                list.forEach { msg ->
                    ChatItem(
                        navController = navController,
                        isOnlyOpeningMessage = false,
                        item = msg,
                        isCurrentPage = isCurrentPage,
                        chatViewModel = chatViewModel,
                        voiceCallRecordingIndex = voiceCallRecordingIndex,
                        isLatestMessage = false,
                        isGuideVisible = isGuideVisible,
                        messageFontSizeSp = messageFontSizeSp,
                    )
                }
            }
        }
    } else {
        VoiceChatHistoryCollapsed(
            messages = list,
            onClick = {
                expanded = true
                onCollapseChange()
            },
            recordingReplayKey = replayKey,
            recording = recording,
            modifier = modifier,
        )
    }
}
