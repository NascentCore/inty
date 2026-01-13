package com.ai.intellimate.chat

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.audio.OpeningPlayState
import com.ai.intellimate.boost.BoostError
import com.ai.intellimate.boost.BoostException
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.ui.BoostSheet
import com.ai.intellimate.chat.ui.BackToTop
import com.ai.intellimate.chat.ui.ChatInput
import com.ai.intellimate.chat.ui.ChatMorePanel
import com.ai.intellimate.chat.ui.ChatSettingsDrawer
import com.ai.intellimate.chat.ui.ChatTopBar
import com.ai.intellimate.chat.ui.EnergyCelebrationBanner
import com.ai.intellimate.chat.ui.ImagePickItem
import com.ai.intellimate.chat.ui.KeepTalkingFloatingButton
import com.ai.intellimate.chat.ui.PremiumModelTag
import com.ai.intellimate.chat.ui.ScrollToBottomButton
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.profile.ModifyProfileViewModel
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.UnlimitChatDialog
import com.ai.intellimate.ui.components.AgentBackground
import com.ai.intellimate.utils.isUserCreatedPrivateRole
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private const val LOAD_MORE_NEAR_TOP_THRESHOLD = 3
private const val LOAD_MORE_MIN_EXTRA_ITEMS = 5

var KEY_BOARD_HEIGHT_MAX = 1

/** ChatPage 页面来源常量 - 用于统计曝光事件 */
object ChatPageSource {
    const val CHAT_ACTIVITY = "chat_activity" // 在 ChatActivity 中
    const val MAIN_ACTIVITY_HOME_TAB =
        "main_activity_home_tab" // 在 MainActivity 的 HorizontalPager 中（默认来源，首次进入或从 chat tab 进入）
    const val FROM_PREVIOUS_AGENT = "from_previous_agent" // 在 HorizontalPager 中从上一个 agent 滑动而来
}

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
) {

    val userProfileViewModel = viewModel<ModifyProfileViewModel>()
    val context = LocalContext.current
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val isQueryMsgsCompleted by chatViewModel.isQueryMsgsCompleted.collectAsState()
    val chatMessages by chatViewModel.msgs.collectAsState()

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

    val hasLoadingMessage =
        remember(chatMessages) {
            chatMessages.any { msg ->
                val hasGeneratedImage = msg.hasGeneratedImage()
                val generatedImageUrl = msg.getGeneratedImageUrl()
                msg.content == "loading_animation" &&
                    !hasGeneratedImage &&
                    generatedImageUrl != "loading"
            }
        }

    // 获取开关状态用于页面曝光事件和 UI 显示
    val showKeepTalking by SettingStateManager.showKeepTalkingFlow.collectAsState()
    val autoPlayVoice by SettingStateManager.autoPlayAudioFlow.collectAsState()
    val autoPlayAnimation by SettingStateManager.autoPlayAnimationFlow.collectAsState()
    val chatFontSizeSp by SettingStateManager.chatFontSizeFlow.collectAsState()
    val chatListFullScreen by SettingStateManager.chatListFullScreenFlow.collectAsState()

    // 记录上次上报的 key，避免在同一页面状态下重复上报
    // 使用 agentInfo?.id 作为 key 的一部分，确保不同 Agent 的页面会分别上报
    val lastReportedKey = remember(agentInfo?.id) { mutableStateOf<String?>(null) }
    // 记录上一个 Agent ID，用于判断是否从其他 agent 滑动而来（HorizontalPager 场景）
    val previousAgentId = remember { mutableStateOf<String?>(null) }

    LaunchedEffect(
        isCurrentPage,
        agentInfo?.id,
        showKeepTalking,
        autoPlayVoice,
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
                "${agentInfo?.id}_${pageSource}_${showKeepTalking}_${autoPlayVoice}_${autoPlayAnimation}"

            // 如果 key 发生变化，说明需要上报新的事件
            // 这确保了：1) 首次曝光时上报 2) Agent 切换时上报 3) 页面来源变化时上报 4) 开关状态变化时上报
            if (lastReportedKey.value != currentKey) {
                // 上报 ChatPage 页面曝光事件
                FirebaseManager.logEvent(
                    FirebaseManager.Events.CHAT_PAGE_VIEW,
                    FirebaseManager.safeEventParams(
                        "page_source" to pageSource,
                        "agent_id" to (agentInfo?.id ?: "unknown"),
                        "agent_name" to (agentInfo?.name ?: "unknown"),
                        "keep_talking_enabled" to showKeepTalking,
                        "auto_play_voice_enabled" to autoPlayVoice,
                        "auto_play_animation_enabled" to autoPlayAnimation,
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

    LaunchedEffect(chatViewModel) {
        chatViewModel.queryMsgs()
        chatViewModel.initVoiceService(context)
    }

    LifecycleResumeEffect(isCurrentPage) {
        chatViewModel.syncLatestMessages()
        onPauseOrDispose { chatViewModel.pauseVoicePlayback() }
    }

    DisposableEffect(chatViewModel, isCurrentPage) {
        onDispose {
            if (!isCurrentPage) {
                chatViewModel.resetVoicePlayback()
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

    val imeHeight = WindowInsets.ime.getBottom(density)
    KEY_BOARD_HEIGHT_MAX = maxOf(imeHeight, KEY_BOARD_HEIGHT_MAX)
    val ratio = 1 - imeHeight.toFloat() / KEY_BOARD_HEIGHT_MAX.toFloat() // 计算出键盘当前弹出/回收进度

    val isKeyboardVisible = imeHeight > 0
    onKeyboardVisible(isKeyboardVisible)
    val bottomPadding = UiConfigs.ChatPage.ChatInput.BottomSpacerHeight

    fun onKeepTalkingChange(enabled: Boolean) {
        SettingStateManager.updateShowKeepTalking(enabled)
    }

    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    var showMorePanel by remember { mutableStateOf(false) }
    var morePanelHeight by remember { mutableStateOf(0.dp) }
    var showPremiumDialog by remember { mutableStateOf(false) }

    val inputFocusRequester = remember(agentInfo?.id) { FocusRequester() }
    val snackbarHostState = remember { SnackbarHostState() }

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
                Spacer(Modifier.height(48.dp))

                agentInfo?.let { info ->
                    ChatTopBar(
                        navController,
                        modifier = Modifier.fillMaxWidth().padding(start = 18.dp),
                        agentInfo = info,
                        fontSize = 15.sp,
                        avatarWidth = UiConfigs.ChatTopBar.AvatarSize,
                        earnedPoints = null,
                        onClickCall = {
                            scope.launch {
                                if (agentInfo?.isDeleted == true) {
                                    ToastUtils.showShort(R.string.str_agent_is_deleted)
                                } else {
                                    onCall()
                                }
                            }
                        },
                        onClickMore = {
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
                            navController.navigate(Routes.Me.VipCenter)
                            //
                            // VipCenterActivity.launch(context,
                            // VipCenterActivity.CHAT_PAGE)
                        }
                        showPremiumDialog = false
                    }
                }

                val chatMessages by chatViewModel.msgs.collectAsState()
                val isLoadingMore by chatViewModel.isLoadingMore.collectAsState()
                val hasMoreMessages by chatViewModel.hasMoreMessages.collectAsState()

                val layoutInfo = listState.layoutInfo
                val visibleItemsForUi = layoutInfo.visibleItemsInfo
                val totalItemsForUi = layoutInfo.totalItemsCount
                val lastVisibleIndexForUi = visibleItemsForUi.maxOfOrNull { it.index } ?: -1
                val hasEnoughDataForUi =
                    totalItemsForUi > visibleItemsForUi.size + LOAD_MORE_MIN_EXTRA_ITEMS
                val isNearTopForUi =
                    totalItemsForUi > 0 &&
                        lastVisibleIndexForUi >= (totalItemsForUi - LOAD_MORE_NEAR_TOP_THRESHOLD)
                val hasScrolledForUi =
                    listState.firstVisibleItemIndex > 0 ||
                        listState.firstVisibleItemScrollOffset > 0
                val showLoadMoreUi =
                    hasMoreMessages &&
                        (isLoadingMore ||
                            (hasEnoughDataForUi && isNearTopForUi && hasScrolledForUi))
                val imagePickMessageId by chatViewModel.imagePickMessageId.collectAsState()

                // 判断是否需要播放开场白语音（移到LazyColumn外部）
                val shouldDelayShowOpening =
                    remember(
                        agentInfo?.id,
                        agentInfo?.opening_audio_url,
                        isQueryMsgsCompleted,
                        isCurrentPage,
                        isGuideVisible,
                        chatMessages.size,
                    ) {
                        agentInfo?.let { agent ->
                            val actualChatMessages =
                                chatMessages.filter { !it.isOpening() && it.role != "system" }
                            val isOnlyOpeningMessage = actualChatMessages.isEmpty()
                            val hasPlayedOpening = OpeningPlayState.agentOpeningPlayed(agent.id)
                            val safeAgentId = agent.id
                            val audioUrl = agent.opening_audio_url

                            // 判断是否需要自动播放开场白语音
                            agent.opening.isNotEmpty() &&
                                isOnlyOpeningMessage &&
                                !hasPlayedOpening &&
                                isQueryMsgsCompleted &&
                                safeAgentId.isNotEmpty() &&
                                audioUrl.isNotEmpty() &&
                                IntySetting.isAutoPlayAudio() &&
                                !isGuideVisible
                        } ?: false
                    }

                // 控制开场白显示状态（移到LazyColumn外部）
                var showOpeningItem by remember(agentInfo?.id) { mutableStateOf(false) }

                // 如果需要延迟显示，延迟1.5秒后显示（移到LazyColumn外部）
                LaunchedEffect(
                    shouldDelayShowOpening,
                    isQueryMsgsCompleted,
                    isCurrentPage,
                    agentInfo?.id,
                ) {
                    if (agentInfo?.id == null || !isQueryMsgsCompleted) {
                        showOpeningItem = false
                        return@LaunchedEffect
                    }

                    if (isCurrentPage) {
                        if (shouldDelayShowOpening) {
                            // 如果需要播放语音，先隐藏，延迟1.5秒后显示
                            delay(1000)
                        }

                        showOpeningItem = true
                    }
                }

                // 非全屏模式下，先添加空白区域
                if (!chatListFullScreen) {
                    Spacer(Modifier.weight(UiConfigs.ChatPage.chatListBlankZone))
                }

                val lazyColumnModifier =
                    if (chatListFullScreen) {
                        // 全屏模式：使用 weight(1f) 保持现有布局
                        Modifier.weight(1f).padding(horizontal = 16.dp)
                    } else {
                        // 非全屏模式：使用剩余空间（1 - chatListBlankZone）
                        Modifier.weight(1f - UiConfigs.ChatPage.chatListBlankZone)
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp)
                    }

                LazyColumn(modifier = lazyColumnModifier, state = listState, reverseLayout = true, contentPadding = PaddingValues(top = 360.dp)) {
                    item { Spacer(Modifier.height(16.dp)) }

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
                                        ToastUtils.showShort(R.string.chat_save_user_photo_success)
                                    }
                                },
                                modifier =
                                    Modifier.padding(vertical = 16.dp).size(210.5.dp, 312.5.dp),
                            )
                        }
                    }

                    val filteredChatMessages = chatMessages.filter { !it.isOpening() }
                    runCatching {
                            if (filteredChatMessages.isNotEmpty()) {
                                val messagesCopy = filteredChatMessages.toList()
                                val items =
                                    messagesCopy.filter {
                                        !(it.role == "user" && it.content == "continue")
                                    }
                                if (items.isNotEmpty()) {
                                    itemsIndexed(
                                        items,
                                        key = { index, info ->
                                            info.localMsgId.ifEmpty {
                                                "${index}_${info.role}_${info.content.hashCode()}_${index}"
                                            }
                                        },
                                    ) { index, item ->
                                        runCatching {
                                                if (index < items.size) {
                                                    val hasGeneratedImage = item.hasGeneratedImage()
                                                    val isImageMessage =
                                                        item.content.isEmpty() && hasGeneratedImage
                                                    // latest 消息用于控制 ChatItem 内部的操作区（如
                                                    // 👍/👎、生图入口等）
                                                    // 这里需要包含“纯图片消息”（content 为空但有
                                                    // generated image），否则图片预览下方无法显示
                                                    // 👍/👎
                                                    val isLatestAssistantMessageForActions =
                                                        index == 0 &&
                                                            item.role == "assistant" &&
                                                            item.content != "loading_animation" &&
                                                            !item.isOpening()

                                                    ChatItem(
                                                        navController,
                                                        item,
                                                        isCurrentPage = isCurrentPage,
                                                        chatViewModel = chatViewModel,
                                                        isLatestMessage =
                                                            isLatestAssistantMessageForActions,
                                                        isGuideVisible = isGuideVisible,
                                                        messageFontSizeSp = chatFontSizeSp,
                                                    )
                                                }
                                                Spacer(Modifier.height(16.dp))
                                            }
                                            .onFailure { e ->
                                                // 渲染失败时显示错误占位符
                                                Box(
                                                    modifier =
                                                        Modifier.fillMaxWidth()
                                                            .height(60.dp)
                                                            .background(
                                                                Color.Red.copy(alpha = 0.1f)
                                                            )
                                                ) {
                                                    Text(
                                                        text = "Message loading failed",
                                                        color = Color.White,
                                                        modifier = Modifier.align(Alignment.Center),
                                                    )
                                                }
                                                Spacer(Modifier.height(16.dp))
                                            }
                                    }
                                }
                            }
                        }
                        .onFailure { e ->
                            item {
                                Box(
                                    modifier =
                                        Modifier.fillMaxWidth()
                                            .height(100.dp)
                                            .background(Color.Red.copy(alpha = 0.1f))
                                ) {
                                    Text(
                                        text = "Chat history loading failed, please retry",
                                        color = Color.White,
                                        modifier = Modifier.align(Alignment.Center),
                                    )
                                }
                            }
                        }

                    val showIntroOpeningTop =
                        isQueryMsgsCompleted && ((!hasMoreMessages) || chatMessages.isEmpty())

                    if (showIntroOpeningTop) {
                        item {
                            agentInfo?.let { agent ->
                                val shouldShowOpening = agent.opening.isNotEmpty()
                                if (shouldShowOpening && showOpeningItem) {
                                    Column {
                                        val openingMessage =
                                            MsgInfo(
                                                content = agent.opening,
                                                role = "assistant",
                                                meta_data =
                                                    MsgInfo.MsgMetaData(
                                                        agentId = agent.id,
                                                        isOpening = true,
                                                    ),
                                                audio_url = agent.opening_audio_url,
                                            )

                                        Spacer(Modifier.height(16.dp))
                                        ChatItem(
                                            navController,
                                            openingMessage,
                                            isCurrentPage = isCurrentPage,
                                            chatViewModel = chatViewModel,
                                            isGuideVisible = isGuideVisible,
                                            messageFontSizeSp = chatFontSizeSp,
                                        )
                                        Spacer(Modifier.height(16.dp))
                                    }
                                }
                            }
                        }
                        item {
                            agentInfo?.intro?.let { info ->
                                if (info.isNotEmpty()) {
                                    AgentInfoChatCard(info)
                                    Spacer(Modifier.height(16.dp))
                                }
                            }
                        }
                    }

                    if (showLoadMoreUi) {
                        item {
                            Box(
                                modifier = Modifier.fillMaxWidth().height(60.dp),
                                contentAlignment = Alignment.Center,
                            ) {
                                if (isLoadingMore) {
                                    CircularProgressIndicator(
                                        color = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.width(24.dp).height(24.dp),
                                    )
                                } else {
                                    Text(
                                        text = "Pull to load more",
                                        color =
                                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                }
                            }
                        }
                    }
                }

                LaunchedEffect(hasMoreMessages, isLoadingMore, chatMessages.size) {
                    snapshotFlow {
                            listState.firstVisibleItemIndex to
                                listState.firstVisibleItemScrollOffset
                        }
                        .collect { (firstVisibleIndex, scrollOffset) ->
                            delay(100)
                            val layoutInfo = listState.layoutInfo
                            val visibleItems = layoutInfo.visibleItemsInfo
                            val totalItemsCount = layoutInfo.totalItemsCount
                            val lastVisibleIndex = visibleItems.maxOfOrNull { it.index } ?: 0

                            val hasEnoughData =
                                totalItemsCount > visibleItems.size + LOAD_MORE_MIN_EXTRA_ITEMS
                            val isNearTop =
                                totalItemsCount > 0 &&
                                    lastVisibleIndex >=
                                        (totalItemsCount - LOAD_MORE_NEAR_TOP_THRESHOLD)
                            val hasScrolled = firstVisibleIndex > 0 || scrollOffset > 0
                            val shouldLoadMore = hasEnoughData && isNearTop && hasScrolled

                            if (shouldLoadMore && hasMoreMessages && !isLoadingMore) {
                                chatViewModel.loadMoreMessages()
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
                    val effectiveBottomPadding =
                        if (showMorePanel)
                            morePanelHeight + UiConfigs.ChatPage.ChatInput.BottomSpacerHeight
                        else bottomPadding

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
                        )
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

            val chatMessagesForButton by chatViewModel.msgs.collectAsState()
            val hasLatestAssistantMessage =
                chatMessagesForButton.firstOrNull { msg ->
                    val hasGeneratedImage = msg.hasGeneratedImage()
                    val isImageMessage = msg.content.isEmpty() && hasGeneratedImage
                    msg.role == "assistant" &&
                        msg.content != "loading_animation" &&
                        !isImageMessage &&
                        !msg.isOpening()
                } != null

            val hasLoadingMessageForButton =
                chatMessagesForButton.any { msg ->
                    val hasGeneratedImage = msg.hasGeneratedImage()
                    val generatedImageUrl = msg.getGeneratedImageUrl()
                    msg.content == "loading_animation" &&
                        !hasGeneratedImage &&
                        generatedImageUrl != "loading"
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
            BackToTop(
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
            )

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
                onClick = { chatViewModel.sendKeepTalkingMessage() },
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

                        try {
                            chatViewModel.reset()
                            resetSuccess = true
                        } catch (_: Throwable) {
                            ToastUtils.showShort(R.string.reset_failed_msg)
                        }
                    }
                },
                onCall = {
                    showMorePanel = false
                    onCall()
                },
            )
        }

        ChatSettingsDrawer(
            chatViewModel = chatViewModel,
            agentInfo = agentInfo,
            drawerState = drawerState,
            onKeepTalkingChange = { enabled -> onKeepTalkingChange(enabled) },
            navController = navController,
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
        // - 提供 "Boost now" 按钮确认投入积分
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

    LaunchedEffect(agentInfo?.id, isCurrentPage, shouldAutoFocusInput) {
        if (!isCurrentPage) return@LaunchedEffect

        if (showMorePanel || agentInfo == null) {
            suppressFocusCallback.value = true
            focusManager.clearFocus()
            return@LaunchedEffect
        }

        if (shouldAutoFocusInput) {
            delay(50)
            inputFocusRequester.requestFocus()
        } else {
            suppressFocusCallback.value = true
            focusManager.clearFocus()
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
    val showDialog by chatViewModel.showLimitDialog.collectAsState()
    //    val context = LocalContext.current
    if (showDialog) {
        val data =
            ChatDialogData(
                R.drawable.img_unlimit_dialog_bg,
                stringResource(R.string.str_unlimit_dialog_content),
                stringResource(R.string.str_unlimit_btn_text),
            )
        UnlimitChatDialog(
            data,
            onCancel = { chatViewModel.dismissDialog() },
            onSure = {
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    navController.navigate(Routes.Me.VipCenter)
                    //                    VipCenterActivity.launch(context,
                    // VipCenterActivity.CHAT_PAGE)
                }
                chatViewModel.dismissDialog()
            },
            onMoreInfo = {
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    navController.navigate(Routes.Me.VipCenter)
                    //                    VipCenterActivity.launch(context,
                    // VipCenterActivity.CHAT_PAGE)
                }
                chatViewModel.dismissDialog()
            },
        )
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
                            navController.navigate(Routes.Me.VipCenter)
                            //                            VipCenterActivity.launch(context,
                            // VipCenterActivity.CHAT_PAGE)
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
                            navController.navigate(Routes.Me.VipCenter)
                            //                            VipCenterActivity.launch(context,
                            // VipCenterActivity.CHAT_PAGE)
                        }
                    }

                    ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {}
                }
                chatViewModel.dismissImageGenerationDialog()
            },
        )
    }
}
