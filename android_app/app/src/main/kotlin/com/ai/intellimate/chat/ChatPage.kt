package com.ai.intellimate.chat

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentConstants
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.firebase.logEvent
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.exclude
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imeAnimationTarget
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.paging.ItemSnapshotList
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import coil3.SingletonImageLoader
import coil3.asDrawable
import coil3.request.ImageRequest
import coil3.request.SuccessResult
import coil3.size.Size as CoilSize
import com.ai.intellimate.R
import com.ai.intellimate.agent.generate.CreateRoleNavigationState
import com.ai.intellimate.boost.BoostConfig
import com.ai.intellimate.boost.BoostError
import com.ai.intellimate.boost.BoostException
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.ui.BoostSheet
import com.ai.intellimate.chat.touch.CharacterBackgroundLayout
import com.ai.intellimate.chat.touch.CharacterTouchActionFormatter
import com.ai.intellimate.chat.touch.CharacterTouchCoordinateMapper
import com.ai.intellimate.chat.ui.ChatInput
import com.ai.intellimate.chat.ui.ChatModeSelectorDialog
import com.ai.intellimate.chat.ui.ChatMorePanel
import com.ai.intellimate.chat.ui.ChatSettingsDrawer
import com.ai.intellimate.chat.ui.ChatTopBar
import com.ai.intellimate.chat.ui.EnergyCelebrationBanner
import com.ai.intellimate.chat.ui.ImagePickItem
import com.ai.intellimate.chat.ui.KeepTalkingFloatingButton
import com.ai.intellimate.chat.ui.OfficialAssistantFaqQuestions
import com.ai.intellimate.chat.ui.PremiumModelTag
import com.ai.intellimate.chat.ui.ScrollToBottomButton
import com.ai.intellimate.chat.ui.VipAgentUnlockDialog
import com.ai.intellimate.chat.ui.officialAssistantFaqItems
import com.ai.intellimate.chat.uistate.ChatUIState
import com.ai.intellimate.chat.uistate.MessageItem
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.profile.ModifyProfileViewModel
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.UnlimitChatDialog
import com.ai.intellimate.ui.components.AgentBackground
import com.ai.intellimate.utils.isUserCreatedPrivateRole
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val LOAD_MORE_NEAR_TOP_THRESHOLD = 3
private const val LOAD_MORE_MIN_EXTRA_ITEMS = 5

var KEY_BOARD_HEIGHT_MAX = 1

/** 消息项类型：普通消息或语音消息组 */
sealed class ChatMessageItem {
    data class NormalMessage(val message: MsgInfo) : ChatMessageItem()

    data class VoiceMessageGroup(val messages: List<MsgInfo>, val groupId: String) :
        ChatMessageItem()
}

/**
 * 将原始消息列表按「普通消息 / 语音消息组」分组，返回用于 LazyColumn 的 MessageItem 列表。 连续的用户+AI
 * 语音对话会合并为一组（CallMessageIndexs），其余为单条 MessageIndex。 某条 message 为 null（如 Paging
 * placeholder）时按普通空消息处理。
 *
 * 索引约定：MessageIndex.index 与 CallMessageIndexs.messages 中的每个值均为 messages 的下标， 与 LazyPagingItems
 * 同序，渲染时用 messages[item.index] / messages[it] 取对应消息。
 *
 * @param messages 原始消息（倒序，新消息在前），getOrNull 可能返回 null（placeholder）
 * @return 分组后的消息项列表，索引均指向 messages 中的位置
 */
private fun proFixMessages(messages: ItemSnapshotList<MessageEntity>): List<MessageItem> {
    val result = mutableListOf<MessageItem>()
    val currentVoiceGroupIndices = mutableListOf<Int>()
    var voiceSessionId: String? = null

    messages.forEachIndexed { index, info ->
        if (info?.content == "continue" && info.role == "user") return@forEachIndexed

        if (info == null) {
            if (currentVoiceGroupIndices.isNotEmpty()) {
                result.add(MessageItem.CallMessageIndexs(currentVoiceGroupIndices.reversed()))
                currentVoiceGroupIndices.clear()
            }
            result.add(MessageItem.MessageIndex(index))
        } else {
            if (info.isVoice) {

                if (voiceSessionId != info.metaData.voiceSessionId) {
                    if (currentVoiceGroupIndices.isNotEmpty()) {
                        result.add(
                            MessageItem.CallMessageIndexs(currentVoiceGroupIndices.reversed())
                        )
                        currentVoiceGroupIndices.clear()
                    }

                    voiceSessionId = info.metaData.voiceSessionId
                }

                currentVoiceGroupIndices.add(index)
            } else if (info.role == "user" && currentVoiceGroupIndices.isNotEmpty()) {
                currentVoiceGroupIndices.add(index)
            } else if (currentVoiceGroupIndices.isNotEmpty()) {
                result.add(MessageItem.CallMessageIndexs(currentVoiceGroupIndices.reversed()))
                result.add(MessageItem.MessageIndex(index))
                currentVoiceGroupIndices.clear()
            } else {
                result.add(MessageItem.MessageIndex(index))
            }
        }
    }

    if (currentVoiceGroupIndices.isNotEmpty()) {
        result.add(MessageItem.CallMessageIndexs(currentVoiceGroupIndices.reversed()))
        currentVoiceGroupIndices.clear()
    }

    return result
}

/** ChatPage 页面来源常量 - 用于统计曝光事件 */
object ChatPageSource {
    const val CHAT_ACTIVITY = "chat_activity" // 在 ChatActivity 中
    const val MAIN_ACTIVITY_HOME_TAB =
        "main_activity_home_tab" // 在 MainActivity 的 HorizontalPager 中（默认来源，首次进入或从 chat tab 进入）
    const val FROM_PREVIOUS_AGENT = "from_previous_agent" // 在 HorizontalPager 中从上一个 agent 滑动而来
}

internal fun shouldDisplayOfficialAssistantCreateButton(
    isOfficialAssistantChat: Boolean,
    isKeyboardVisible: Boolean,
): Boolean = isOfficialAssistantChat && !isKeyboardVisible

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun ChatPage(
    navController: NavController,
    modifier: Modifier,
    chatViewModel: ChatViewModel,
    contentPadding: PaddingValues = PaddingValues(),
    showBackButton: Boolean = false,
    isCurrentPage: Boolean = true,
    shouldAutoFocusInput: Boolean = true,
    onInputFocusChange: (Boolean) -> Unit = {},
    onKeyboardVisible: (Boolean) -> Unit = {},
    onCall: () -> Unit = {},
    pageSourceOverride: String? = null, // 如果提供，则使用此 pageSource（通常来自 ChatActivity）
    isGuideVisible: Boolean = false,
    shouldShowBoostSheetOnOpen: Boolean = false,
    debugAgentIndex: Int? = null,
    fromPage: String? = null,
    refreshMessageCount: Int = 0,
) {

    val userProfileViewModel = viewModel<ModifyProfileViewModel>()
    val context = LocalContext.current
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val officialAssistantFaqQuickItems = remember { officialAssistantFaqItems() }
    val isOfficialAssistantChat = AgentConstants.isIntelliMateAgent(agentInfo?.id, agentInfo?.name)

    // 用户自建私有角色不展示 Boost 相关功能
    val shouldShowBoostUi = agentInfo?.isUserCreatedPrivateRole() != true

    // 为角色应援/Boost 功能
    // 这里是 AI 生成代码，不清楚 UI 上有什么影响
    val isDebugMode = HeartAppUtils.isAppDebugMode()
    val boostState by BoostManager.boostState.collectAsState()
    var showBoostSheet by remember { mutableStateOf(false) }
    var pendingBoostSheet by
        remember(shouldShowBoostSheetOnOpen) { mutableStateOf(shouldShowBoostSheetOnOpen) }
    val scope = rememberCoroutineScope()
    val showBoostError: (BoostError) -> Unit = { error ->
        val messageRes =
            when (error) {
                BoostError.NotEnoughPoints -> R.string.boost_toast_not_enough_points
                BoostError.DailyRewardAlreadyClaimed -> R.string.boost_daily_reward_already
                else -> R.string.boost_toast_generic_error
            }
        ToastUtils.showShort(messageRes)
    }
    val messages = chatViewModel.messages.collectAsLazyPagingItems()
    val agent by chatViewModel.agentFlow.collectAsState()
    val messageItems by
        remember(isCurrentPage) {
            LogUtils.d("Chat Message预处理 消息数=${messages.itemSnapshotList.size}")
            derivedStateOf {
                proFixMessages(messages.itemSnapshotList) +
                    listOf(MessageItem.Opening, MessageItem.Intro)
            }
        }

    val hasLoadingMessage by remember {
        derivedStateOf {
            messages.itemSnapshotList.any { msg ->
                msg != null &&
                    msg.content == "loading_animation" &&
                    !msg.hasGeneratedImage() &&
                    msg.getGeneratedImageUrl() != "loading"
            }
        }
    }

    val hasUserSentMessageInOfficialAssistant by
        chatViewModel.hasUserSentMessageInOfficialAssistant.collectAsState()
    val shouldShowOfficialAssistantFaqQuestions by
        remember(isOfficialAssistantChat) {
            derivedStateOf { isOfficialAssistantChat && !hasUserSentMessageInOfficialAssistant }
        }
    // 获取开关状态用于页面曝光事件和 UI 显示
    val showKeepTalking by SettingStateManager.showKeepTalkingFlow.collectAsState(false)
    val autoPlayVoice by SettingStateManager.autoPlayAudioFlow.collectAsState(false)
    val autoPlayAnimation by SettingStateManager.autoPlayAnimationFlow.collectAsState()
    val sendUxUiGestureSignals by SettingStateManager.sendUxUiGestureSignalsFlow.collectAsState()
    val chatFontSizeSp by SettingStateManager.chatFontSizeFlow.collectAsState()
    val chatListFullScreen by SettingStateManager.chatListFullScreenFlow.collectAsState()
    val chatSettings by chatViewModel.chatSettings.collectAsState()
    val chatVoiceOptions by chatViewModel.chatVoiceOptions.collectAsState()
    val isLoadingChatVoices by chatViewModel.isLoadingChatVoices.collectAsState()

    // 记录上次上报的 key，避免在同一页面状态下重复上报
    // 使用 agentInfo?.id 作为 key 的一部分，确保不同 Agent 的页面会分别上报
    val lastReportedKey = remember(agentInfo?.id) { mutableStateOf<String?>(null) }
    // 记录上一个 Agent ID，用于判断是否从其他 agent 滑动而来（HorizontalPager 场景）
    val previousAgentId = remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        chatViewModel.vipRequest.collect {
            navController.navigate(Routes.Me.vipCenter("chat_vip_request"))
        }
    }

    LaunchedEffect(refreshMessageCount, isCurrentPage) {
        if (isCurrentPage && refreshMessageCount > 0) {
            LogUtils.d("chatPage: refreshCount = $refreshMessageCount")
            chatViewModel.loadRecentMessages(refreshMessageCount)
        }
    }

    LaunchedEffect(
        isCurrentPage,
        agentInfo?.id,
        showKeepTalking,
        autoPlayVoice,
        sendUxUiGestureSignals,
        pageSourceOverride,
    ) {
        // 确保 ChatPage 页面曝光事件（CHAT_PAGE_VIEW）在所有场景下都能正确上报
        if (isCurrentPage && agentInfo?.id != null) {
            // 确定页面来源
            val pageSource: String =
                pageSourceOverride
                    ?: if (showBackButton) {
                        // 理论上不应该出现这种情况，但为了安全起见保留
                        ChatPageSource.CHAT_ACTIVITY
                    } else {
                        // 判断是否从上一个 agent 滑动而来
                        val isFromPreviousAgent =
                            previousAgentId.value != null &&
                                previousAgentId.value != agentInfo?.id &&
                                previousAgentId.value != ""

                        if (isFromPreviousAgent) {
                            ChatPageSource.FROM_PREVIOUS_AGENT
                        } else {
                            // 首次进入或从 chat tab 进入
                            ChatPageSource.MAIN_ACTIVITY_HOME_TAB
                        }
                    }

            // 生成唯一 key，用于判断是否需要上报（避免在同一状态下重复上报）
            // 包含 Agent ID、页面来源和开关状态，确保这些关键参数变化时会重新上报
            val currentKey =
                "${agentInfo?.id}_${pageSource}_${showKeepTalking}_${autoPlayVoice}_${autoPlayAnimation}_${sendUxUiGestureSignals}"

            // 如果 key 发生变化，说明需要上报新的事件
            // 这确保了：1) 首次曝光时上报 2) Agent 切换时上报 3) 页面来源变化时上报 4) 开关状态变化时上报
            if (lastReportedKey.value != currentKey) {
                // 上报 ChatPage 页面曝光事件
                FirebaseManager.logEvent(
                    FirebaseManager.Events.CHAT_PAGE_VIEW,
                    FirebaseManager.safeEventParams(
                        "from_page" to (fromPage ?: "unknown"),
                        "page_source" to pageSource,
                        "agent_id" to (agentInfo?.id ?: "unknown"),
                        "agent_name" to (agentInfo?.name ?: "unknown"),
                        "keep_talking_enabled" to showKeepTalking,
                        "auto_play_voice_enabled" to autoPlayVoice,
                        "auto_play_animation_enabled" to autoPlayAnimation,
                        "send_ux_ui_gesture_signals" to sendUxUiGestureSignals,
                    ),
                )

                lastReportedKey.value = currentKey
            }

            // 更新 previousAgentId，用于下次判断页面来源
            previousAgentId.value = agentInfo?.id

            // 如果提供了 pageSourceOverride（通常来自 ChatActivity），说明 BaseActivity 已经追踪了页面访问
            // 此时 ChatPage 不应该重复追踪 PageTrackingHelper，避免覆盖 BaseActivity 的 page_source
            if (pageSourceOverride != null) {
                return@LaunchedEffect
            }

            // 在 MainActivity 中使用时，需要自己追踪 PageTrackingHelper
            PageTrackingHelper.trackPageView(
                "ChatPage",
                if (showBackButton) "ChatActivity" else "MainActivity",
                mapOf(
                    "agent_id" to (agentInfo?.id ?: "unknown"),
                    "agent_name" to (agentInfo?.name ?: "unknown"),
                    "show_back_button" to showBackButton,
                    "page_source" to pageSource,
                    // 添加开关状态参数，用于分析不同配置下的用户行为
                    "keep_talking_enabled" to showKeepTalking,
                    "auto_play_voice_enabled" to autoPlayVoice,
                    "auto_play_animation_enabled" to autoPlayAnimation,
                    "send_ux_ui_gesture_signals" to sendUxUiGestureSignals,
                ),
            )
        }
    }

    // 从 Explore 页面点击 "Boost" 按钮跳转到聊天页面时，自动打开 BoostSheet
    LaunchedEffect(agentInfo?.id, pendingBoostSheet) {
        if (agentInfo != null && pendingBoostSheet) {
            // 私有自建角色不允许打开 BoostSheet
            if (shouldShowBoostUi) {
                showBoostSheet = true
            }
            pendingBoostSheet = false
        }
    }

    LaunchedEffect(chatViewModel) { chatViewModel.initVoiceService(context) }

    LifecycleResumeEffect(isCurrentPage) { onPauseOrDispose { chatViewModel.pauseVoicePlayback() } }

    DisposableEffect(chatViewModel, isCurrentPage) {
        val wasCurrentPage = isCurrentPage
        onDispose {
            if (!wasCurrentPage) {
                chatViewModel.resetVoicePlayback()
            } else {
                chatViewModel.clearForMomentExposureCycle()
            }
        }
    }

    LaunchedEffect(agentInfo?.id) {
        if (agentInfo?.id != null) {
            chatViewModel.stopNonCurrentAgentPlayback()
        }
    }

    val density = LocalDensity.current
    val focusManager = LocalFocusManager.current
    val suppressFocusCallback = remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    val imeHeight = WindowInsets.ime.getBottom(density)
    KEY_BOARD_HEIGHT_MAX = maxOf(imeHeight, KEY_BOARD_HEIGHT_MAX)
    val ratio = 1 - imeHeight.toFloat() / KEY_BOARD_HEIGHT_MAX.toFloat() // 计算出键盘当前弹出/回收进度

    val isKeyboardVisible = imeHeight > 0
    val shouldShowOfficialAssistantQuickActions =
        shouldDisplayOfficialAssistantCreateButton(isOfficialAssistantChat, isKeyboardVisible)
    onKeyboardVisible(isKeyboardVisible)
    val bottomPadding = UiConfigs.ChatPage.ChatInput.BottomSpacerHeight

    fun onKeepTalkingChange(enabled: Boolean) {
        coroutineScope.launch { SettingStateManager.updateShowKeepTalking(enabled) }
    }

    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    var showMorePanel by remember { mutableStateOf(false) }
    var morePanelHeight by remember { mutableStateOf(0.dp) }
    var showPremiumDialog by remember { mutableStateOf(false) }
    var isVoiceInputActive by remember { mutableStateOf(false) }

    val inputFocusRequester = remember(agentInfo?.id) { FocusRequester() }
    val snackbarHostState = remember { SnackbarHostState() }
    val uiState by chatViewModel.uiState.collectAsState()
    val backgroundTouchSourceUrl =
        remember(agentInfo?.id, agentInfo?.background, agentInfo?.avatar) {
            resolveBackgroundTouchSourceUrl(agentInfo)
        }
    val backgroundSourceImageSize =
        rememberBackgroundTouchSourceImageSize(
            imageUrl = backgroundTouchSourceUrl,
            isOfficialAssistantChat = isOfficialAssistantChat,
        )
    var backgroundCaptureSize by remember(agentInfo?.id) { mutableStateOf(IntSize.Zero) }
    val backgroundTouchMinSwipeDistancePx =
        with(density) { UiConfigs.ChatPage.backgroundTouchMinSwipeDistance.toPx() }

    if (
        uiState.vipAgentLockType == ChatUIState.VipAgentLockType.DIALOG &&
            showBackButton &&
            messages.loadState.refresh is LoadState.NotLoading
    ) {
        agentInfo?.let { agent ->
            VipAgentUnlockDialog(
                agent = agent,
                unlockByCredits = chatViewModel::chatUnlockByCredits,
                unlockBySub = {
                    FirebaseManager.Events.VIP_AGENT_UNLOCK.logEvent(
                        "agent_id" to agent.id,
                        "unlock_method" to "subscription",
                    )
                    navController.navigate(Routes.Me.vipCenter("chat_vip_agent_unlock"))
                },
                onDismissRequest = {
                    navController.navigateUp()

                    chatViewModel.clearAgent()
                    FirebaseManager.Events.VIP_AGENT_UNLOCK.logEvent(
                        "agent_id" to agent.id,
                        "unlock_method" to "close_dialog",
                    )
                },
            )
        }
    }

    Box(
        modifier =
            modifier.padding(contentPadding).pointerInput(Unit) {
                detectTapGestures(
                    onTap = {
                        suppressFocusCallback.value = true
                        focusManager.clearFocus()
                        if (isCurrentPage) {
                            onInputFocusChange(false)
                        }
                    }
                )
            }
    ) {
        // 只在非 ChatActivity 场景显示背景图（ChatActivity 中背景图已在外层显示）
        if (!showBackButton) {
            AgentBackground(
                agentInfo = agentInfo,
                showGradients = true,
                isLoading = hasLoadingMessage,
                isCurrentPage = isCurrentPage,
                enableAnimatedBackground = autoPlayAnimation,
            )
        }

        // Full-size layer: captures tap/swipe in the top fraction of the background (when gesture
        // signals are on), maps to source image coordinates, and sends a touch action message.
        Box(
            modifier =
                Modifier.fillMaxSize()
                    .onSizeChanged { size -> backgroundCaptureSize = size }
                    .pointerInput(
                        isCurrentPage,
                        sendUxUiGestureSignals,
                        uiState.vipAgentLockType,
                        backgroundCaptureSize,
                        backgroundSourceImageSize,
                        backgroundTouchMinSwipeDistancePx,
                        agentInfo?.id,
                    ) {
                        val sourceSize = backgroundSourceImageSize ?: return@pointerInput
                        val backgroundLayout =
                            buildCharacterBackgroundLayout(
                                containerSize = backgroundCaptureSize,
                                sourceImageSize = sourceSize,
                            ) ?: return@pointerInput
                        val shouldIgnoreTouch: (Offset) -> Boolean = { point ->
                            !isCurrentPage ||
                                !sendUxUiGestureSignals ||
                                uiState.vipAgentLockType != ChatUIState.VipAgentLockType.NONE ||
                                point.y >
                                    backgroundCaptureSize.height *
                                        UiConfigs.ChatPage.backgroundTouchCaptureMaxYRatio
                        }

                        detectTapGestures(
                            onTap = { tapPoint ->
                                if (shouldIgnoreTouch(tapPoint)) return@detectTapGestures
                                val mappedPoint =
                                    CharacterTouchCoordinateMapper.mapPoint(
                                        layout = backgroundLayout,
                                        touchX = tapPoint.x,
                                        touchY = tapPoint.y,
                                    ) ?: return@detectTapGestures
                                val action =
                                    CharacterTouchActionFormatter.buildTapAction(
                                        startPoint = mappedPoint,
                                        sourceImageWidth = sourceSize.width,
                                        sourceImageHeight = sourceSize.height,
                                        useAsteriskMarker =
                                            agentInfo?.useDoubleAsteriskActionMarker() == true,
                                    )
                                chatViewModel.sendBackgroundTouchAction(action)
                            }
                        )
                        var swipeStartPoint: Offset? = null
                        var swipeEndPoint: Offset? = null
                        detectDragGestures(
                            onDragStart = { startOffset ->
                                swipeStartPoint = startOffset
                                swipeEndPoint = startOffset
                            },
                            onDrag = { _, dragAmount ->
                                val currentPoint = swipeEndPoint ?: return@detectDragGestures
                                swipeEndPoint = currentPoint + dragAmount
                            },
                            onDragEnd = {
                                val start = swipeStartPoint
                                val end = swipeEndPoint
                                swipeStartPoint = null
                                swipeEndPoint = null
                                if (start == null || end == null) return@detectDragGestures
                                if (shouldIgnoreTouch(start) || shouldIgnoreTouch(end)) {
                                    return@detectDragGestures
                                }
                                val dx = end.x - start.x
                                val dy = end.y - start.y
                                val movedDistance = kotlin.math.sqrt(dx * dx + dy * dy)
                                if (movedDistance < backgroundTouchMinSwipeDistancePx) {
                                    return@detectDragGestures
                                }

                                val mappedStart =
                                    CharacterTouchCoordinateMapper.mapPoint(
                                        layout = backgroundLayout,
                                        touchX = start.x,
                                        touchY = start.y,
                                    ) ?: return@detectDragGestures
                                val mappedEnd =
                                    CharacterTouchCoordinateMapper.mapPoint(
                                        layout = backgroundLayout,
                                        touchX = end.x,
                                        touchY = end.y,
                                    ) ?: return@detectDragGestures
                                val action =
                                    CharacterTouchActionFormatter.buildSwipeAction(
                                        startPoint = mappedStart,
                                        endPoint = mappedEnd,
                                        sourceImageWidth = sourceSize.width,
                                        sourceImageHeight = sourceSize.height,
                                        useAsteriskMarker =
                                            agentInfo?.useDoubleAsteriskActionMarker() == true,
                                    )
                                chatViewModel.sendBackgroundTouchAction(action)
                            },
                            onDragCancel = {
                                swipeStartPoint = null
                                swipeEndPoint = null
                            },
                        )
                    }
        )

        val drawerState = remember { mutableStateOf(DrawerValue.Closed) }
        val keyboard = LocalSoftwareKeyboardController.current

        LifecycleResumeEffect(keyboard) { onPauseOrDispose { keyboard?.hide() } }

        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0),
            snackbarHost = {
                SnackbarHost(snackbarHostState) {
                    Snackbar(
                        snackbarData = it,
                        containerColor = Color(0xFF322F35),
                        contentColor = Color.White,
                    )
                }
            },
        ) { innerPadding ->
            val listState = rememberLazyListState()
            // 聊天页面滚动位置状态：true 表示用户在最新消息位置，false 表示用户已滚动到历史消息
            // 此状态用于控制两个浮动按钮的显示：
            // - 在最新消息位置：显示 Keep Talking 按钮（如果启用）
            // - 在历史消息位置：显示滚动到底部按钮
            var isAtLatestMessage by remember { mutableStateOf(true) }
            var isAtChatStart by remember { mutableStateOf(false) }
            val chatModel by chatViewModel.selectedChatMode.collectAsState(null)
            var showChatModeSelector by remember { mutableStateOf(false) }

            // 监听滚动位置变化，实时更新 isAtLatestMessage 状态
            // 当 firstVisibleItemIndex == 0 且 scrollOffset == 0 时，表示用户正在查看最新消息
            LaunchedEffect(listState) {
                snapshotFlow {
                        Triple(
                            listState.firstVisibleItemIndex,
                            listState.firstVisibleItemScrollOffset,
                            listState.canScrollForward,
                        )
                    }
                    .collect { (firstVisibleIndex, scrollOffset, canScrollForward) ->
                        isAtLatestMessage = firstVisibleIndex == 0 && scrollOffset == 0
                        isAtChatStart =
                            listState.layoutInfo.totalItemsCount > 0 && !canScrollForward
                    }
            }

            Column(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
                // 标题栏始终固定在顶部，不随键盘弹起而隐藏
                Spacer(Modifier.height(48.dp))

                agentInfo?.let { info ->
                    ChatTopBar(
                        modifier = Modifier.fillMaxWidth().padding(start = 18.dp),
                        agentInfo = info,
                        earnedPoints = null,
                        showBackButton = showBackButton,
                        onBack = {
                            navController.popBackStack()
                            chatViewModel.clearAgent()
                        },
                        onAgentDetail = { navController.navigate(Routes.Home.agentInfPage(it)) },
                        onClickChatMode = {
                            FirebaseManager.Events.CHAT_MODE_BUTTON_CLICK.logEvent(
                                "agent_id" to agent?.agentId,
                                "agent_name" to agent?.name,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            )
                            showChatModeSelector = true
                        },
                        chatMode = chatModel,
                        showChatModeButton = !isOfficialAssistantChat,
                        onClickCall = {
                            FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                                "click_type" to "call",
                                "agent_id" to agent?.agentId,
                                "agent_name" to agent?.name,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            )

                            scope.launch {
                                if (agentInfo?.isDeleted == true) {
                                    ToastUtils.showShort(R.string.str_agent_is_deleted)
                                } else {
                                    onCall()
                                }
                            }
                        },
                        onClickMore = {
                            FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                                "click_type" to "sidebar",
                                "agent_id" to agent?.agentId,
                                "agent_name" to agent?.name,
                                "user_type" to if (VipStatusHelper.isUserVip()) "vip" else "free",
                            )
                            scope.launch {
                                if (agentInfo?.isDeleted == true) {
                                    ToastUtils.showShort(R.string.str_agent_is_deleted)
                                } else {
                                    if (drawerState.value == DrawerValue.Closed) {
                                        drawerState.value = DrawerValue.Open
                                    } else {
                                        drawerState.value = DrawerValue.Closed
                                    }
                                }
                            }
                        },
                    )

                    if (isDebugMode && debugAgentIndex != null) {
                        Spacer(Modifier.height(8.dp))
                        DebugAgentIndexBadge(
                            modifier = Modifier.padding(start = 18.dp),
                            index = debugAgentIndex,
                            agentName = info.name,
                        )
                    }
                }

                Spacer(Modifier.height(16.dp))

                if (
                    agentInfo != null &&
                        !vipStatus.isSubscribed &&
                        UiConfigs.ChatPage.showSubscriptionButton
                ) {
                    PremiumModelTag(
                        onClick = {
                            scope.launch {
                                if (agentInfo?.isDeleted == true) {
                                    ToastUtils.showShort(R.string.str_agent_is_deleted)
                                } else {
                                    showPremiumDialog = true
                                }
                            }
                        }
                    )
                    Spacer(Modifier.height(8.dp))
                    if (showPremiumDialog) {
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            navController.navigate(Routes.Me.vipCenter("chat_premium_dialog"))
                            //
                            // VipCenterActivity.launch(context,
                            // VipCenterActivity.CHAT_PAGE)
                        }
                        showPremiumDialog = false
                    }
                }

                val imagePickMessageId by chatViewModel.imagePickMessageId.collectAsState()
                // 消息列表：全屏/半屏均占满高度；半屏时在 LazyColumn 顶部叠加渐变，使消息从顶部渐变消失

                val lazyColumnModifier =
                    Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp)

                if (showChatModeSelector) {
                    ChatModeSelectorDialog(
                        onDismiss = { showChatModeSelector = false },
                        selectedChatModeId = chatModel?.id,
                        viewModel = chatViewModel,
                    )
                }

                BoxWithConstraints(modifier = lazyColumnModifier) {
                    val density = LocalDensity.current
                    val chatViewHeight = remember {
                        with(density) { (maxHeight - 48.dp).roundToPx() }
                    }

                    val listModifier =
                        if (chatListFullScreen) {
                            Modifier.fillMaxSize()
                        } else {
                            Modifier.fillMaxSize()
                                .graphicsLayer(compositingStrategy = CompositingStrategy.Offscreen)
                                .drawWithCache {
                                    onDrawWithContent {
                                        drawContent()
                                        drawRect(
                                            brush =
                                                Brush.verticalGradient(
                                                    0f to Color.Transparent,
                                                    0.25f to Color.Transparent,
                                                    UiConfigs.ChatPage.chatListBlankZone to
                                                        Color.Black,
                                                ),
                                            blendMode = BlendMode.DstIn,
                                        )
                                    }
                                }
                        }
                    LazyColumn(
                        modifier = listModifier,
                        state = listState,
                        reverseLayout = true,
                        contentPadding =
                            PaddingValues(top = UiConfigs.ChatPage.chatPageLazyColumnGapTop),
                    ) {
                        item { Spacer(Modifier.height(16.dp)) }

                        if (shouldShowOfficialAssistantFaqQuestions) {
                            item {
                                OfficialAssistantFaqQuestions(
                                    items = officialAssistantFaqQuickItems,
                                    onQuestionClick = { item ->
                                        chatViewModel.setInputMessage(
                                            context.getString(item.questionResId)
                                        )
                                        inputFocusRequester.requestFocus()
                                        onInputFocusChange(true)
                                        FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                                            "click_type" to "official_faq_question",
                                            "agent_id" to agentInfo?.id,
                                            "agent_name" to agentInfo?.name,
                                            "faq_title" to context.getString(item.titleResId),
                                            "user_type" to
                                                if (VipStatusHelper.isUserVip()) "vip" else "free",
                                        )
                                    },
                                )
                            }
                        }

                        if (!imagePickMessageId.isNullOrEmpty()) {
                            item("ImagePicker") {
                                val isUserUploading by
                                    userProfileViewModel.isAppearanceUploading.collectAsState()

                                ImagePickItem(
                                    isLoading = isUserUploading,
                                    onSkip = { chatViewModel.generateImageForMessage() },
                                    onImageSelected = {
                                        userProfileViewModel.setUserAppearance(it) {
                                            chatViewModel.generateImageForMessage()
                                            ToastUtils.showShort(
                                                R.string.chat_save_user_photo_success
                                            )
                                        }
                                    },
                                    modifier =
                                        Modifier.padding(vertical = 16.dp).size(210.5.dp, 312.5.dp),
                                )
                            }
                        }

                        itemsIndexed(
                            items = messageItems,
                            key = { index, item ->
                                when (item) {
                                    is MessageItem.Opening -> "opening"
                                    is MessageItem.Intro -> "intro"
                                    is MessageItem.MessageIndex ->
                                        messages.peek(item.index)?.let { "${it.id}${it.indexId}" }
                                            ?: index
                                    is MessageItem.CallMessageIndexs ->
                                        messages.peek(item.messages.first())?.let {
                                            "${it.id}${it.indexId}"
                                        } ?: index
                                }
                            },
                        ) { index, item ->
                            when (item) {
                                is MessageItem.Intro -> {
                                    AgentInfoChatCard(agent?.intro.orEmpty())
                                    Spacer(Modifier.height(16.dp))
                                }
                                is MessageItem.Opening -> {
                                    val isOnlyOpeningMessage by remember {
                                        derivedStateOf {
                                            messages.itemSnapshotList.isEmpty() &&
                                                messages.loadState.isIdle
                                        }
                                    }
                                    val openingMessage =
                                        MessageEntity(
                                            id = "",
                                            content = agent?.opening.orEmpty(),
                                            role = "assistant",
                                            audioUrl = agent?.openingAudioUrl,
                                            metaData =
                                                MessageEntity.MetaData(
                                                    agentId = agent?.agentId.orEmpty(),
                                                    isOpening = true,
                                                ),
                                        )

                                    Column {
                                        Spacer(Modifier.height(16.dp))
                                        ChatItem(
                                            navController,
                                            item = openingMessage,
                                            isOnlyOpeningMessage = isOnlyOpeningMessage,
                                            isCurrentPage = isCurrentPage,
                                            chatViewModel = chatViewModel,
                                            isGuideVisible = isGuideVisible,
                                            messageFontSizeSp = chatFontSizeSp,
                                        )
                                    }
                                }
                                is MessageItem.MessageIndex -> {
                                    val message = messages[item.index]

                                    if (message != null) {
                                        ChatItem(
                                            navController,
                                            item = message,
                                            agentName = agent?.name,
                                            isOnlyOpeningMessage = false,
                                            isCurrentPage = isCurrentPage,
                                            chatViewModel = chatViewModel,
                                            isLatestMessage = index == 0,
                                            isGuideVisible = isGuideVisible,
                                            messageFontSizeSp = chatFontSizeSp,
                                        )
                                    } else {
                                        Spacer(Modifier.height(50.dp))
                                    }
                                }
                                is MessageItem.CallMessageIndexs -> {
                                    CallMessages(
                                        messages = item.messages.map { messages[it] },
                                        navController = navController,
                                        chatViewModel = chatViewModel,
                                        isCurrentPage = isCurrentPage,
                                        isGuideVisible = isGuideVisible,
                                        messageFontSizeSp = chatFontSizeSp,
                                        modifier = Modifier.fillMaxWidth(),
                                        onCollapseChange = {
                                            listState.requestScrollToItem(
                                                index + 2,
                                                -chatViewHeight,
                                            )
                                        },
                                    )
                                }
                            }
                        }
                    }
                }

                if (agentInfo?.isDeleted == true) {
                    Box(
                        modifier =
                            Modifier.fillMaxWidth()
                                .height(48.dp)
                                .padding(horizontal = 16.dp)
                                .clip(RoundedCornerShape(24.dp))
                                .background(Color(0x9937303D)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = stringResource(R.string.str_chat_disabled),
                            color = Color(0x8CFFFFFF),
                        )
                    }
                } else {
                    if (shouldShowOfficialAssistantQuickActions) {
                        val createEntryConfig = UiConfigs.ChatPage.OfficialAssistantCreateEntry
                        // AI 实现小结：
                        // 1) 官方助手聊天页输入框上方提供两个独立快捷入口（单行水平可滚动）：
                        //    - Test my MBTI type（测试我的 MBTI 类型）：回填结构化提示词并立即发送；
                        //    - + Create your own iMate（创建我的 iMate）：进入创建角色流程。
                        // 2) 两个入口都遵循同一显隐规则：仅在官方助手页且键盘收起时展示；
                        // 3) 入口位置固定在输入框上方，避免与消息流和输入区交互冲突。
                        Row(
                            modifier =
                                Modifier.horizontalScroll(rememberScrollState())
                                    .padding(
                                        start = createEntryConfig.HorizontalPadding,
                                        end = createEntryConfig.HorizontalPadding,
                                    ),
                            horizontalArrangement =
                                Arrangement.spacedBy(createEntryConfig.BottomSpacing),
                        ) {
                            OfficialAssistantQuickActionButton(
                                text = stringResource(R.string.chat_official_mbti_test_button),
                                onClick = {
                                    chatViewModel.setInputMessage(
                                        context.getString(R.string.chat_official_mbti_test_prompt)
                                    )
                                    chatViewModel.sendMsg()
                                    FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                                        "click_type" to "official_test_mbti_type",
                                        "agent_id" to agentInfo?.id,
                                        "agent_name" to agentInfo?.name,
                                        "user_type" to
                                            if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    )
                                },
                            )
                            OfficialAssistantQuickActionButton(
                                text = stringResource(R.string.chat_official_create_imate_button),
                                onClick = {
                                    FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                                        "click_type" to "official_create_imate",
                                        "agent_id" to agentInfo?.id,
                                        "agent_name" to agentInfo?.name,
                                        "user_type" to
                                            if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    )
                                    navController.currentBackStackEntry
                                        ?.savedStateHandle
                                        ?.set(
                                            CreateRoleNavigationState.EntrySourceKey,
                                            CreateRoleNavigationState
                                                .EntrySourceOfficialAssistantChat,
                                        )
                                    navController.navigate(Routes.Creat.createRole(""))
                                },
                            )
                        }
                    }

                    val effectiveBottomPadding =
                        if (showMorePanel)
                            morePanelHeight + UiConfigs.ChatPage.ChatInput.BottomSpacerHeight
                        else bottomPadding

                    if (
                        uiState.vipAgentLockType == ChatUIState.VipAgentLockType.INPUT ||
                            (uiState.vipAgentLockType == ChatUIState.VipAgentLockType.DIALOG &&
                                !showBackButton)
                    ) {
                        val inputConfig = UiConfigs.ChatPage.ChatInput
                        val unlockCost = BoostConfig.UNLOCK_VIP_AGENT_COST
                        Box(
                            modifier =
                                Modifier.padding(
                                        start = inputConfig.HorizontalPadding,
                                        top = inputConfig.TopPadding,
                                        end = inputConfig.HorizontalPadding,
                                        bottom = inputConfig.BottomSpacerHeight,
                                    )
                                    .fillMaxWidth()
                                    .height(inputConfig.MinHeight)
                                    .clip(RoundedCornerShape(inputConfig.CornerRadius))
                                    .background(AppColors.DarkPurpleOverlay60)
                                    .noRippleClickable { chatViewModel.chatUnlockByCredits() },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                text =
                                    stringResource(R.string.unlock_with_credits_price, unlockCost),
                                color = Color.White,
                                fontSize = 14.sp,
                            )
                        }
                    } else {
                        CompositionLocalProvider(
                            LocalDensity provides
                                Density(
                                    density = LocalDensity.current.density,
                                    fontScale = 1f, // 核心：禁用字体缩放
                                )
                        ) {
                            ChatInput(
                                chatViewModel = chatViewModel,
                                onSendMessage = { chatViewModel.sendMsg() },
                                onToggleMorePanel = {
                                    FirebaseManager.Events.CHAT_PAGE_CLICK.logEvent(
                                        "click_type" to "more",
                                        "agent_id" to agent?.agentId,
                                        "agent_name" to agent?.name,
                                        "user_type" to
                                            if (VipStatusHelper.isUserVip()) "vip" else "free",
                                    )

                                    showMorePanel = !showMorePanel
                                    focusManager.clearFocus()
                                },
                                showMorePanel = showMorePanel,
                                bottomPadding = UiConfigs.ChatPage.ChatInput.BottomSpacerHeight,
                                focusRequester = inputFocusRequester,
                                onFocusChange = { focused ->
                                    if (!isCurrentPage) return@ChatInput
                                    if (suppressFocusCallback.value) {
                                        suppressFocusCallback.value = false
                                        return@ChatInput
                                    }
                                    onInputFocusChange(focused)
                                },
                                onVoiceInputActiveChange = { isVoiceInputActive = it },
                            )
                        }
                    }
                }

                val density = LocalDensity.current
                val imeTarget = WindowInsets.imeAnimationTarget.exclude(WindowInsets.navigationBars)

                LaunchedEffect(Unit) {
                    snapshotFlow { imeTarget.getBottom(density) }
                        .collect { heightPx ->
                            with(density) {
                                heightPx
                                    .toDp()
                                    .value
                                    .takeIf { it > 200 }
                                    ?.let { SettingStateManager.setKeyboardHeight(it) }
                            }
                        }
                }

                // 控制输入框底部距离适配morePanel或键盘高度
                val bottomSpaceModifier =
                    if (showMorePanel) {
                        val navigationBarHeight = WindowInsets.navigationBars.getBottom(density)
                        val navigationBarHeightDp = with(density) { navigationBarHeight.toDp() }

                        if (showBackButton) {
                            Modifier.height(morePanelHeight)
                        } else {
                            Modifier.height(
                                morePanelHeight - contentPadding.calculateBottomPadding() +
                                    navigationBarHeightDp
                            )
                        }
                    } else {
                        Modifier.consumeWindowInsets(contentPadding).imePadding()
                    }

                Spacer(modifier = bottomSpaceModifier)
            }

            val hasLatestAssistantMessage by remember {
                derivedStateOf {
                    messages.itemSnapshotList.firstOrNull { msg ->
                        msg != null &&
                            msg.role == "assistant" &&
                            msg.content != "loading_animation" &&
                            !(msg.content.isEmpty() && msg.hasGeneratedImage()) &&
                            !msg.isOpening
                    } != null
                }
            }

            val hasLoadingMessageForButton by remember {
                derivedStateOf {
                    messages.itemSnapshotList.any { msg ->
                        msg != null &&
                            msg.content == "loading_animation" &&
                            !msg.hasGeneratedImage() &&
                            msg.getGeneratedImageUrl() != "loading"
                    }
                }
            }

            // Keep Talking 按钮显示逻辑：
            // 1. 用户开启了 Keep Talking 功能
            // 2. 存在最新的 AI 助手消息
            // 3. 用户当前在最新消息位置（未滚动到历史记录）
            // 4. Agent 未被删除
            // 当用户滚动到历史记录时，此按钮会自动隐藏
            val showKeepTalkingButton =
                showKeepTalking &&
                    hasLatestAssistantMessage &&
                    isAtLatestMessage &&
                    agentInfo?.isDeleted != true
            val isKeepTalkingEnabled = !hasLoadingMessageForButton

            // 滚动到底部按钮显示逻辑：
            // 当用户不在最新消息位置时（已滚动到历史记录），始终显示此按钮
            // 点击后平滑滚动回最新消息位置
            // 即使回到第一条消息，只要有新消息（不在最新消息位置），也显示此按钮
            val showScrollToBottomButton = !isAtLatestMessage

            // 回到聊天开始按钮显示逻辑：
            // 当用户不在最新消息位置且不在聊天开始位置时显示
            // 当用户到达聊天开始位置时，此按钮隐藏
            val showBackToTopButton = !isAtLatestMessage && !isAtChatStart

            // 聊天输入框的高度（从 UiConfigs 获取）
            val chatInputHeight = UiConfigs.ChatPage.ChatInput.EstimatedHeight
            // 按钮底部边距：如果显示更多面板，使用面板高度；否则使用正常的底部边距
            val buttonBottomMargin =
                if (showMorePanel) morePanelHeight + UiConfigs.ChatPage.ChatInput.BottomSpacerHeight
                else bottomPadding
            val keyboardHeightDp = with(LocalDensity.current) { imeHeight.toDp() }

            // Keep Talking 按钮的底部偏移量（基础位置）
            // 基础位置 = 输入框高度 + 底部边距 + 键盘高度（如果不在 ChatActivity 中）
            val keepTalkingButtonBaseBottomOffset =
                if (showBackButton) {
                    // ChatActivity 中：输入框高度 + 底部边距
                    chatInputHeight + buttonBottomMargin
                } else {
                    // MainActivity 中：输入框高度 + 底部边距 + 键盘高度
                    chatInputHeight + buttonBottomMargin + keyboardHeightDp
                }

            // 计算滚动到底部按钮的垂直位置
            // 如果 Keep Talking 按钮可见，则滚动到底部按钮位于其上方，避免重叠
            // 否则，滚动到底部按钮使用与 Keep Talking 按钮相同的位置
            // 注意：只有当 ScrollToBottomButton 可见时才考虑 KeepTalking 的影响，
            // 避免在按钮隐藏时位置突然变化导致跳动
            val scrollToBottomButtonBottomOffset = keepTalkingButtonBaseBottomOffset

            val scrollToStartButtonBottomOffset =
                scrollToBottomButtonBottomOffset +
                    UiConfigs.ChatPage.FloatingScrollButton.ButtonSize +
                    UiConfigs.ChatPage.ScrollToHistoryButtons.VerticalSpacing

            // 滚动到聊天开始按钮：当用户滚动到历史消息时显示在右下角（位于"回到最新"按钮上方）
            // 功能：点击后平滑滚动到最旧消息位置（LazyColumn reverseLayout，最旧消息对应最大索引）
            /*BackToTop(
                modifier =
                    Modifier.align(Alignment.BottomCenter)
                        .padding(
                            bottom = scrollToStartButtonBottomOffset,
                            end = UiConfigs.ChatPage.FloatingScrollButton.RightPadding,
                        ),
                visible = showBackToTopButton,
                onClick = {
                    scope.launch {
                        val totalItemsCount = listState.layoutInfo.totalItemsCount
                        if (totalItemsCount > 0) {
                            listState.animateScrollToItem(totalItemsCount - 1)
                        }
                    }
                },
            )*/

            // 滚动到底部按钮：当用户不在最新消息位置时显示在右下角
            // 功能：点击后平滑滚动回最新消息位置（LazyColumn 使用 reverseLayout，索引 0 为最新消息）
            // 当有新消息时，始终显示此按钮，即使回到第一条消息也不隐藏
            ScrollToBottomButton(
                modifier =
                    Modifier.align(Alignment.BottomCenter)
                        .padding(
                            bottom = scrollToBottomButtonBottomOffset,
                            end = UiConfigs.ChatPage.FloatingScrollButton.RightPadding,
                        ),
                visible = showScrollToBottomButton,
                onClick = {
                    scope.launch {
                        // 平滑滚动到索引 0（最新消息位置）
                        listState.animateScrollToItem(0)
                    }
                },
            )

            // Keep Talking 按钮：当用户在最新消息位置时显示在右下角
            // 功能：点击后发送 "continue" 消息，让 AI 继续对话
            // 当用户滚动到历史记录时，此按钮会自动隐藏，避免与滚动到底部按钮重叠
            KeepTalkingFloatingButton(
                modifier =
                    Modifier.align(Alignment.BottomEnd)
                        .padding(bottom = keepTalkingButtonBaseBottomOffset),
                visible = showKeepTalkingButton,
                enabled = isKeepTalkingEnabled,
                onClick = {
                    if (
                        messages.loadState.refresh is LoadState.NotLoading || messages.itemCount > 0
                    ) {
                        if (uiState.vipAgentLockType == ChatUIState.VipAgentLockType.NONE) {
                            chatViewModel.sendKeepTalkingMessage()
                        } else {
                            ToastUtils.showShort(R.string.str_character_not_unlocked)
                        }
                    } else {
                        ToastUtils.showShort(R.string.str_please_wait_loading)
                    }
                },
            )
        }

        val resetSucMsg = stringResource(R.string.reset_suc_msg)
        var resetSuccess by remember { mutableStateOf(false) }

        // 使用rememberCoroutineScope启动Snackbar存在bug
        LaunchedEffect(snackbarHostState) {
            snapshotFlow { resetSuccess }
                .collect {
                    if (it) {
                        snackbarHostState.showSnackbar(message = resetSucMsg)
                        resetSuccess = false
                    }
                }
        }

        val hasUserMessages by chatViewModel.hasUserMessagesInChat.collectAsState()
        if (showMorePanel) {
            ChatMorePanel(
                navController,
                agentInfo = agentInfo,
                chatViewModel = chatViewModel,
                onDismiss = { showMorePanel = false },
                onHeightChange = { h -> morePanelHeight = h },
                onReset = {
                    scope.launch {
                        showMorePanel = false
                        if (isOfficialAssistantChat) {
                            chatViewModel.clearOfficialAssistantUserMessageSent()
                        }

                        try {
                            chatViewModel.reset()
                            resetSuccess = true
                            if (!VipStatusHelper.isUserVip()) {
                                ToastUtils.showShort(
                                    R.string.credits_deducted,
                                    BoostConfig.CHAT_RESET_COST,
                                )
                            }
                        } catch (e: BoostException) {
                            if (e.error == BoostError.NotEnoughPoints) {
                                ToastUtils.showShort(R.string.credits_not_enough)
                            } else {
                                ToastUtils.showShort(R.string.reset_failed_msg)
                            }
                        } catch (_: Throwable) {
                            ToastUtils.showShort(R.string.reset_failed_msg)
                        }
                    }
                },
                onCall = {
                    showMorePanel = false
                    chatViewModel.markOfficialAssistantUserMessageSent()
                    onCall()
                },
                hasUserMessages = hasUserMessages,
            )
        }

        ChatSettingsDrawer(
            agentInfo = agentInfo,
            drawerState = drawerState,
            onKeepTalkingChange = { enabled -> onKeepTalkingChange(enabled) },
            navController = navController,
            selectedChatVoiceId = agentInfo?.id?.let { chatSettings[it]?.voice_id },
            chatVoiceOptions = chatVoiceOptions,
            isLoadingChatVoices = isLoadingChatVoices,
            onChatVoiceSelected = { voiceId -> chatViewModel.updateChatVoiceSetting(voiceId) },
            showBackButton = showBackButton,
        )

        if (shouldShowBoostUi) {
            EnergyCelebrationBanner(
                totalPoints = boostState.chatMessagePoints,
                enabled = isCurrentPage,
                modifier =
                    Modifier.align(Alignment.TopCenter)
                        .padding(start = 16.dp, end = 16.dp, top = 16.dp),
            )
        }

        ShowLimitDialog(navController, chatViewModel)
        ShowImageGenerationDialog(navController, chatViewModel)

        // Boost 功能弹窗：显示半屏底部弹窗，允许用户投入积分
        // 触发场景：
        // 1. 从 Explore 页面的 Boost Tab 点击 "Boost" 按钮跳转到聊天页面时自动打开（通过 shouldShowBoostSheetOnOpen 参数控制）
        // 2. 在角色主页点击 BoostStatusChip 时打开（AgentInfoScreen.kt）
        // UI 效果：
        // - 显示角色信息（头像、名称）
        // - 显示可用积分（availablePoints）和积分投入滑块（100 pts 步长）
        // - 提供 "Hype now" 按钮确认投入积分
        // 交互流程：
        // - onBoostConfirmed: 用户确认投入积分 → 调用 BoostManager.boostAgent() → 成功后插入系统消息到聊天流 → 关闭弹窗
        // - onDismiss: 用户点击外部区域或取消按钮 → 直接关闭弹窗
        // 错误处理：Boost 操作失败时显示 Toast 错误提示（积分不足、已领取奖励等）
        agentInfo?.let { info ->
            if (shouldShowBoostUi && showBoostSheet) {
                BoostSheet(
                    navController,
                    agentInfo = info,
                    availablePoints = boostState.availablePoints,
                    onBoostConfirmed = { points ->
                        scope.launch {
                            try {
                                val result = BoostManager.boostAgent(info, points)
                                ToastUtils.showShort(
                                    context.getString(
                                        R.string.boost_toast_success_points,
                                        result.pointsSpent,
                                        info.name,
                                    )
                                )
                                chatViewModel.appendBoostSystemMessage(
                                    agent = info,
                                    points = result.pointsSpent,
                                    totalBoosts = result.info.boostCount,
                                )
                                showBoostSheet = false
                            } catch (e: BoostException) {
                                showBoostError(e.error)
                                showBoostSheet = false
                            } catch (e: Exception) {
                                showBoostError(BoostError.NotEnoughPoints)
                                showBoostSheet = false
                            }
                        }
                    },
                    onDismiss = { showBoostSheet = false },
                )
            }
        }

        val needLogin by chatViewModel.requestLogin.collectAsState()
        if (needLogin) {
            chatViewModel.dismissLoginRequest()
        }
    }

    // 如果切换到“私有自建角色”，确保不会残留显示 BoostSheet
    LaunchedEffect(shouldShowBoostUi) {
        if (!shouldShowBoostUi && showBoostSheet) {
            showBoostSheet = false
            pendingBoostSheet = false
        }
    }

    LaunchedEffect(agentInfo?.id, isCurrentPage, shouldAutoFocusInput, messages.loadState.refresh) {
        if (!isCurrentPage) return@LaunchedEffect

        if (showMorePanel || agentInfo == null) {
            suppressFocusCallback.value = true
            focusManager.clearFocus()
            return@LaunchedEffect
        }

        if (
            shouldAutoFocusInput &&
                (messages.loadState.refresh is LoadState.NotLoading || messages.itemCount > 0)
        ) {
            delay(50)
            inputFocusRequester.requestFocus()
        } else {
            suppressFocusCallback.value = true
            focusManager.clearFocus()
        }
    }
}

/**
 * URL used for background touch coordinate mapping: custom chat background or agent origin image.
 */
private fun resolveBackgroundTouchSourceUrl(agentInfo: AgentInfo?): String? {
    val currentAgentId = agentInfo?.id ?: return null
    val customBackgroundUrl = IntySetting.getChatBackgroundImage(currentAgentId)
    if (!customBackgroundUrl.isNullOrBlank()) {
        return customBackgroundUrl
    }
    return agentInfo.getOriginShowImage()?.takeIf { it.isNotBlank() }
}

/**
 * Resolves the background image size (px) for touch mapping; official assistant uses drawable, else
 * loads via Coil.
 */
@Composable
private fun rememberBackgroundTouchSourceImageSize(
    imageUrl: String?,
    isOfficialAssistantChat: Boolean,
): IntSize? {
    val context = LocalContext.current
    val imageSizeState =
        produceState<IntSize?>(initialValue = null, imageUrl, isOfficialAssistantChat) {
            if (isOfficialAssistantChat) {
                val drawable = context.getDrawable(R.drawable.img_official_agent_background)
                val width = drawable?.intrinsicWidth ?: 0
                val height = drawable?.intrinsicHeight ?: 0
                value = if (width > 0 && height > 0) IntSize(width, height) else null
                return@produceState
            }
            if (imageUrl.isNullOrBlank()) {
                value = null
                return@produceState
            }

            value = loadOriginalImageSize(context, imageUrl)
        }
    return imageSizeState.value
}

private suspend fun loadOriginalImageSize(
    context: android.content.Context,
    imageUrl: String,
): IntSize? {
    return withContext(Dispatchers.IO) {
        val request = ImageRequest.Builder(context).data(imageUrl).size(CoilSize.ORIGINAL).build()
        val result = SingletonImageLoader.get(context).execute(request)
        if (result !is SuccessResult) {
            return@withContext null
        }

        val drawable = result.image.asDrawable(context.resources)
        val width = drawable.intrinsicWidth
        val height = drawable.intrinsicHeight
        if (width <= 0 || height <= 0) {
            null
        } else {
            IntSize(width, height)
        }
    }
}

/**
 * Builds layout for container→source coordinate mapping; returns null if any dimension is invalid.
 */
private fun buildCharacterBackgroundLayout(
    containerSize: IntSize,
    sourceImageSize: IntSize,
): CharacterBackgroundLayout? {
    if (
        containerSize.width <= 0 ||
            containerSize.height <= 0 ||
            sourceImageSize.width <= 0 ||
            sourceImageSize.height <= 0
    ) {
        return null
    }
    return CharacterBackgroundLayout(
        containerWidthPx = containerSize.width.toFloat(),
        containerHeightPx = containerSize.height.toFloat(),
        sourceImageWidthPx = sourceImageSize.width.toFloat(),
        sourceImageHeightPx = sourceImageSize.height.toFloat(),
    )
}

/**
 * 官方助手聊天页输入框上方快捷入口按钮（Official Assistant Quick Action Button）。
 *
 * 适用范围：
 * - 仅用于官方助手聊天页输入框上方的快捷入口（如“Test my MBTI type / + Create your own iMate”）。
 *
 * 预期视觉效果：
 * - 与聊天输入区域同一视觉语言：圆角、半透明紫底与 [UiConfigs.ChatPage.ChatInput] 一致；
 * - 在官方助手快捷区中与同类按钮同一行水平排列，必要时可横向滚动；
 * - 文案由参数传入，正文字号与输入框 [IntySmallTextField] 一致。
 *
 * 可配置项：
 *
 * @param modifier 外层布局修饰符（用于定位到输入框上方并设置间距）
 * @param text 按钮文案
 * @param onClick 点击回调（可用于回填提示词或导航到创建角色页面）
 */
@Composable
private fun OfficialAssistantQuickActionButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val inputConfig = UiConfigs.ChatPage.ChatInput
    val entryConfig = UiConfigs.ChatPage.OfficialAssistantCreateEntry
    Box(
        modifier =
            modifier
                .background(
                    shape = MaterialTheme.shapes.medium,
                    color = MaterialTheme.colorScheme.surface,
                )
                .border(
                    width = .5.dp,
                    color = MaterialTheme.colorScheme.outline,
                    shape = MaterialTheme.shapes.medium,
                )
                .noRippleClickable { onClick() }
                .padding(
                    horizontal = entryConfig.ContentHorizontalPadding,
                    vertical = inputConfig.VerticalPadding,
                ),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

@Preview(showBackground = true, name = "Single")
@Composable
private fun PreviewOfficialAssistantQuickActionButtonSingle() {
    IntelliMateTheme {
        Surface(color = MaterialTheme.colorScheme.surface) {
            OfficialAssistantQuickActionButton(
                modifier = Modifier.padding(16.dp),
                text = "Create my own iMate",
                onClick = {},
            )
        }
    }
}

@Preview(showBackground = true, name = "Row (official assistant strip)")
@Composable
private fun PreviewOfficialAssistantQuickActionButtonRow() {
    val gap = UiConfigs.ChatPage.OfficialAssistantCreateEntry.BottomSpacing
    IntelliMateTheme {
        Surface(color = MaterialTheme.colorScheme.surface) {
            Row(
                modifier = Modifier.horizontalScroll(rememberScrollState()).padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(gap),
            ) {
                OfficialAssistantQuickActionButton(text = "Test my MBTI type", onClick = {})
                OfficialAssistantQuickActionButton(text = "Create my own iMate", onClick = {})
            }
        }
    }
}

@Composable
private fun DebugAgentIndexBadge(modifier: Modifier = Modifier, index: Int, agentName: String) {
    val label =
        remember(index, agentName) {
            buildString {
                append("#")
                append(index)
                if (agentName.isNotBlank()) {
                    append(" · ")
                    append(agentName)
                }
            }
        }

    Box(
        modifier =
            modifier
                .background(Color.Black.copy(alpha = 0.7f), RoundedCornerShape(6.dp))
                .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(text = label, color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)
    }
}

/** 聊天消息受限的dialog */
@Composable
private fun ShowLimitDialog(navController: NavController, chatViewModel: ChatViewModel) {
    val dialogType by chatViewModel.showChatLimitDialog.collectAsState()
    dialogType?.let { type ->
        when (type) {
            ChatViewModel.ChatLimitDialogType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                val data =
                    ChatDialogData(
                        R.drawable.img_unlimit_dialog_bg,
                        stringResource(R.string.str_unlimit_dialog_content),
                        stringResource(R.string.str_unlimit_btn_text),
                    )
                UnlimitChatDialog(
                    data,
                    onCancel = { chatViewModel.dismissChatLimitDialog() },
                    onSure = {
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            navController.navigate(Routes.Me.vipCenter("chat_unlimit_dialog"))
                        }
                        chatViewModel.dismissChatLimitDialog()
                    },
                    onMoreInfo = {
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            navController.navigate(Routes.Me.vipCenter("chat_unlimit_dialog"))
                        }
                        chatViewModel.dismissChatLimitDialog()
                    },
                )
            }
            ChatViewModel.ChatLimitDialogType.SUBSCRIBER_LIMIT_REACHED -> {
                AlertDialog(
                    onDismissRequest = { chatViewModel.dismissChatLimitDialog() },
                    confirmButton = {
                        TextButton(onClick = { chatViewModel.dismissChatLimitDialog() }) {
                            Text(
                                text =
                                    stringResource(R.string.chat_subscriber_limit_reached_confirm)
                            )
                        }
                    },
                    title = {
                        Text(text = stringResource(R.string.chat_subscriber_limit_reached_title))
                    },
                    text = {
                        Text(text = stringResource(R.string.chat_subscriber_limit_reached_content))
                    },
                )
            }
        }
    }
}

/** 消息生图接口受限时候的弹窗dialog */
@Composable
private fun ShowImageGenerationDialog(navController: NavController, chatViewModel: ChatViewModel) {
    val context = LocalContext.current
    val dialogData by chatViewModel.showImageGenerationDialog.collectAsState()

    dialogData?.let { data ->
        val content =
            when (data.errorType) {
                ChatViewModel.ImageGenerationErrorType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                    stringResource(R.string.image_generation_free_limit_content)
                }

                ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {
                    stringResource(R.string.image_generation_vip_limit_content)
                }
            }

        val dialogDataForUI =
            ChatDialogData(
                R.drawable.img_unlimit_dialog_bg,
                content,
                stringResource(R.string.str_unlimit_btn_text),
            )

        UnlimitChatDialog(
            dialogDataForUI,
            onCancel = { chatViewModel.dismissImageGenerationDialog() },
            onSure = {
                when (data.errorType) {
                    ChatViewModel.ImageGenerationErrorType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            navController.navigate(
                                Routes.Me.vipCenter("chat_image_generation_dialog")
                            )
                        }
                    }

                    ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {}
                }
                chatViewModel.dismissImageGenerationDialog()
            },
            onMoreInfo = {
                when (data.errorType) {
                    ChatViewModel.ImageGenerationErrorType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            navController.navigate(
                                Routes.Me.vipCenter("chat_image_generation_dialog")
                            )
                        }
                    }

                    ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {}
                }
                chatViewModel.dismissImageGenerationDialog()
            },
        )
    }
}
