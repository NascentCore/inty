package com.ai.intellimate.chat

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.ai.intellimate.BottomNavigationBarHeight
import com.ai.intellimate.R
import com.ai.intellimate.chat.ui.ChatInput
import com.ai.intellimate.chat.ui.ChatMorePanel
import com.ai.intellimate.chat.ui.ChatSettingsDrawer
import com.ai.intellimate.chat.ui.ChatTopBar
import com.ai.intellimate.chat.ui.KeepTalkingFloatingButton
import com.ai.intellimate.chat.ui.PremiumModelTag
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.UnlimitChatDialog
import com.ai.intellimate.ui.components.AgentBackground
import com.ai.intellimate.vip.VipCenterActivity
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

// The spacer from the bottom of the chat input to what ever that flows underneath it.
val ChatInputBottomSpacerHeight = 8.dp
private const val LOAD_MORE_NEAR_TOP_THRESHOLD = 3
private const val LOAD_MORE_MIN_EXTRA_ITEMS = 5

var KEY_BOARD_HEIGHT_MAX = 1

/** ChatPage 页面来源常量 - 用于统计曝光事件 */
object ChatPageSource {
    const val CHAT_ACTIVITY = "chat_activity" // 在 ChatActivity 中
    const val MAIN_ACTIVITY_HOME_TAB =
        "main_activity_home_tab" // 在 MainActivity 的 HorizontalPager 中
}

@Composable
internal fun ChatPage(
    modifier: Modifier,
    chatViewModel: ChatViewModel,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
    isCurrentPage: Boolean = true,
    shouldAutoFocusInput: Boolean = true,
    onInputFocusChange: (Boolean) -> Unit = {},
    pageSourceOverride: String? = null, // 如果提供，则使用此 pageSource（通常来自 ChatActivity）
) {

    val context = LocalContext.current
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val isQueryMsgsCompleted by chatViewModel.isQueryMsgsCompleted.collectAsState()
    val chatMessages by chatViewModel.msgs.collectAsState()

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

    LaunchedEffect(
        isCurrentPage,
        agentInfo?.id,
        showKeepTalking,
        autoPlayVoice,
        pageSourceOverride,
    ) {
        if (isCurrentPage) {
            // 如果提供了 pageSourceOverride（通常来自 ChatActivity），说明 BaseActivity 已经追踪了页面访问
            // 此时 ChatPage 不应该重复追踪，避免覆盖 BaseActivity 的 page_source
            if (pageSourceOverride != null) {
                // ChatActivity 已经通过 BaseActivity 追踪了页面访问，包含正确的 page_source
                // 这里不再重复追踪
                return@LaunchedEffect
            }

            // 在 MainActivity 中使用时，需要自己追踪
            val pageSource =
                if (showBackButton) ChatPageSource.CHAT_ACTIVITY
                else ChatPageSource.MAIN_ACTIVITY_HOME_TAB
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
                ),
            )
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

    val gap = if (showBackButton) 0.dp else BottomNavigationBarHeight * ratio
//    val isKeyboardVisible = imeHeight > 0
//    val bottomPadding =
//        when {
//            showBackButton -> ChatInputBottomSpacerHeight
//            isKeyboardVisible -> ChatInputBottomSpacerHeight
//            else -> BottomNavigationBarHeight + ChatInputBottomSpacerHeight
//        }
    val bottomPadding = gap + ChatInputBottomSpacerHeight

    fun onKeepTalkingChange(enabled: Boolean) {
        SettingStateManager.updateShowKeepTalking(enabled)
    }

    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    var showMorePanel by remember { mutableStateOf(false) }
    var morePanelHeight by remember { mutableStateOf(0.dp) }
    var showPremiumDialog by remember { mutableStateOf(false) }

    val inputFocusRequester = remember(agentInfo?.id) { FocusRequester() }

    Box(
        modifier =
            modifier.pointerInput(Unit) {
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
            )
        }

        val drawerState = remember { mutableStateOf(DrawerValue.Closed) }
        val scope = rememberCoroutineScope()

        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0),
        ) { innerPadding ->
            Box(modifier = Modifier.fillMaxSize()) {
                Column(modifier = Modifier.padding(innerPadding).imePadding()) {
                    Spacer(Modifier.height(48.dp))

                    agentInfo?.let { info ->
                        ChatTopBar(
                            modifier = Modifier.fillMaxWidth().padding(start = 18.dp),
                            agentInfo = info,
                            showBackButton = showBackButton,
                            onBack = onBack,
                            fontSize = 15.sp,
                            avatarWidth = 40,
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
                    }

                    Spacer(Modifier.height(16.dp))

                    if (agentInfo != null && !vipStatus.isSubscribed) {
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
                                VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                            }
                            showPremiumDialog = false
                        }
                    }

                    val chatMessages by chatViewModel.msgs.collectAsState()
                    val isLoadingMore by chatViewModel.isLoadingMore.collectAsState()
                    val hasMoreMessages by chatViewModel.hasMoreMessages.collectAsState()
                    val listState = rememberLazyListState()

                    val layoutInfo = listState.layoutInfo
                    val visibleItemsForUi = layoutInfo.visibleItemsInfo
                    val totalItemsForUi = layoutInfo.totalItemsCount
                    val lastVisibleIndexForUi = visibleItemsForUi.maxOfOrNull { it.index } ?: -1
                    val hasEnoughDataForUi =
                        totalItemsForUi > visibleItemsForUi.size + LOAD_MORE_MIN_EXTRA_ITEMS
                    val isNearTopForUi =
                        totalItemsForUi > 0 &&
                            lastVisibleIndexForUi >=
                                (totalItemsForUi - LOAD_MORE_NEAR_TOP_THRESHOLD)
                    val hasScrolledForUi =
                        listState.firstVisibleItemIndex > 0 ||
                            listState.firstVisibleItemScrollOffset > 0
                    val showLoadMoreUi =
                        hasMoreMessages &&
                            (isLoadingMore ||
                                (hasEnoughDataForUi && isNearTopForUi && hasScrolledForUi))

                    LazyColumn(
                        modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                        state = listState,
                        reverseLayout = true,
                    ) {
                        item { Spacer(Modifier.height(16.dp)) }
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
                                                        val hasGeneratedImage =
                                                            item.hasGeneratedImage()
                                                        val isImageMessage =
                                                            item.content.isEmpty() &&
                                                                hasGeneratedImage
                                                        val isLatestAssistantTextMessage =
                                                            index == 0 &&
                                                                item.role == "assistant" &&
                                                                item.content !=
                                                                    "loading_animation" &&
                                                                !isImageMessage

                                                        ChatItem(
                                                            item,
                                                            isCurrentPage = isCurrentPage,
                                                            chatViewModel = chatViewModel,
                                                            isLatestMessage =
                                                                isLatestAssistantTextMessage,
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
                                                            modifier =
                                                                Modifier.align(Alignment.Center),
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
                                    if (shouldShowOpening) {
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
                                        ChatItem(
                                            openingMessage,
                                            isCurrentPage = isCurrentPage,
                                            chatViewModel = chatViewModel,
                                        )
                                        Spacer(Modifier.height(16.dp))
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
                                                MaterialTheme.colorScheme.onSurface.copy(
                                                    alpha = 0.6f
                                                ),
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
                            if (showMorePanel) morePanelHeight else bottomPadding

                        CompositionLocalProvider(    LocalDensity provides Density(
                            density = LocalDensity.current.density,
                            fontScale = 1f               // 核心：禁用字体缩放
                        )) {
                            ChatInput(
                                chatViewModel = chatViewModel,
                                onSendMessage = { chatViewModel.sendMsg() },
                                onToggleMorePanel = { showMorePanel = !showMorePanel },
                                showMorePanel = showMorePanel,
                                bottomPadding = effectiveBottomPadding,
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

                val showKeepTalkingButton = showKeepTalking && hasLatestAssistantMessage
                val isKeepTalkingEnabled = !hasLoadingMessageForButton

                val chatInputEstimatedHeight = 70.dp
                val effectiveBottomPaddingForButton =
                    if (showMorePanel) morePanelHeight else bottomPadding
                val imeHeightDp = with(LocalDensity.current) { imeHeight.toDp() }
                val buttonBottomOffset =
                    if (showBackButton) {
                        chatInputEstimatedHeight + effectiveBottomPaddingForButton
                    } else {
                        chatInputEstimatedHeight + effectiveBottomPaddingForButton + imeHeightDp
                    }

                KeepTalkingFloatingButton(
                    modifier =
                        Modifier.align(Alignment.BottomEnd).padding(bottom = buttonBottomOffset),
                    visible = showKeepTalkingButton,
                    enabled = isKeepTalkingEnabled,
                    onClick = { chatViewModel.sendKeepTalkingMessage() },
                )
            }
        }

        ChatMorePanel(
            visible = showMorePanel,
            agentInfo = agentInfo,
            chatViewModel = chatViewModel,
            onDismiss = { showMorePanel = false },
            onHeightChange = { h -> morePanelHeight = h },
        )

        ChatSettingsDrawer(
            chatViewModel = chatViewModel,
            agentInfo = agentInfo,
            drawerState = drawerState,
            onKeepTalkingChange = { enabled -> onKeepTalkingChange(enabled) },
        )

        ShowLimitDialog(chatViewModel)
        ShowImageGenerationDialog(chatViewModel)

        val needLogin by chatViewModel.requestLogin.collectAsState()
        if (needLogin) {
            chatViewModel.dismissLoginRequest()
        }
    }

    LaunchedEffect(agentInfo?.id, isCurrentPage, showMorePanel, shouldAutoFocusInput) {
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

/** 聊天消息受限的dialog */
@Composable
private fun ShowLimitDialog(chatViewModel: ChatViewModel) {
    val showDialog by chatViewModel.showLimitDialog.collectAsState()
    val context = LocalContext.current
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
                    VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                }
                chatViewModel.dismissDialog()
            },
            onMoreInfo = {
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                }
                chatViewModel.dismissDialog()
            },
        )
    }
}

/** 消息生图接口受限时候的弹窗dialog */
@Composable
private fun ShowImageGenerationDialog(chatViewModel: ChatViewModel) {
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
                            VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
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
                            VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                        }
                    }

                    ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {}
                }
                chatViewModel.dismissImageGenerationDialog()
            },
        )
    }
}
