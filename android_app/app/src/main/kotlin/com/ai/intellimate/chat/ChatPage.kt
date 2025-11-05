package com.ai.intellimate.chat

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.utils.LogUtils
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
import androidx.compose.ui.unit.dp
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
import com.ai.intellimate.login.LoginActivity
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
) {

    val context = LocalContext.current
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val isQueryMsgsCompleted by chatViewModel.isQueryMsgsCompleted.collectAsState()

    // 使用 PageTrackingHelper 进行页面跟踪（仅在页面可见时触发，避免 HorizontalPager 缓存机制导致的误触发）
    LaunchedEffect(isCurrentPage, agentInfo?.id) {
        if (isCurrentPage) {
            // 根据 showBackButton 判断页面来源：true 表示在 ChatActivity 中，false 表示在 MainActivity 的 HorizontalPager 中
            val pageSource =
                if (showBackButton) ChatPageSource.CHAT_ACTIVITY else ChatPageSource.MAIN_ACTIVITY_HOME_TAB
            PageTrackingHelper.trackPageView(
                "ChatPage",
                if (showBackButton) "ChatActivity" else "MainActivity",
                mapOf(
                    "agent_id" to (agentInfo?.id ?: "unknown"),
                    "agent_name" to (agentInfo?.name ?: "unknown"),
                    "show_back_button" to showBackButton,
                    "page_source" to pageSource,
                )
            )
        }
    }

    LaunchedEffect(chatViewModel) {
        chatViewModel.queryMsgs()
        // 初始化语音服务
        chatViewModel.initVoiceService(context)
    }

    // 统一生命周期：页面进入 onPause（包括 Activity 或应用退到后台）时停止音频
    LifecycleResumeEffect(isCurrentPage) {
        // 应用恢复时，增量同步最新消息
        chatViewModel.syncLatestMessages()
        onPauseOrDispose { chatViewModel.pauseVoicePlayback() }
    }

    // 页面生命周期管理：离开页面时重置播放状态
    DisposableEffect(chatViewModel, isCurrentPage) {
        onDispose {
            if (!isCurrentPage) {
                chatViewModel.resetVoicePlayback()
            }
        }
    }

    // 监听agent变化，当agent切换时停止非当前agent的播放
    LaunchedEffect(agentInfo?.id) {
        val currentAgentId = agentInfo?.id
        if (currentAgentId != null) {
            // 当agent切换时，停止非当前agent的音频播放
            chatViewModel.stopNonCurrentAgentPlayback()
        }
    }

    val density = LocalDensity.current
    val focusManager = LocalFocusManager.current
    val suppressFocusCallback = remember { mutableStateOf(false) }

    // 检测键盘状态
    val imeHeight = WindowInsets.ime.getBottom(density)
    val isKeyboardVisible = imeHeight > 0

    // 动态计算底部间距
    val bottomPadding =
        when {
            showBackButton -> ChatInputBottomSpacerHeight // 独立聊天页面：固定
            isKeyboardVisible -> ChatInputBottomSpacerHeight // 首页聊天页面，键盘呼出时
            else -> BottomNavigationBarHeight + ChatInputBottomSpacerHeight // 首页聊天页面，无键盘时
        }

    // Keep talking全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val shouldShowButton by SettingStateManager.showKeepTalkingFlow.collectAsState()

    // Keep talking状态变化回调
    fun onKeepTalkingChange(enabled: Boolean) {
        SettingStateManager.updateShowKeepTalking(enabled)
    }

    // VIP状态
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
        // 背景
        AgentBackground(agentInfo = agentInfo, showGradients = true)

        val drawerState = remember { mutableStateOf(DrawerValue.Closed) }
        val scope = rememberCoroutineScope()

        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0),
        ) { innerPadding ->
            Box(modifier = Modifier.fillMaxSize()) {
                Column(
                    modifier = Modifier
                        .padding(innerPadding)
                        .imePadding()
                ) {
                    Spacer(Modifier.height(48.dp))

                    // 立即显示TopBar和Premium标签（不等待数据加载）
                    agentInfo?.let { info ->
                        ChatTopBar(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(start = 18.dp),
                            agentInfo = info,
                            showBackButton = showBackButton,
                            onBack = onBack,
                            onClickMore = {
                                scope.launch {
                                    // 如果是已经删除的agent，则不可点击，并提示
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

                    // Premium model标签,非vip显示，vip隐藏（20251020的要求）
                    if (agentInfo != null && !vipStatus.isSubscribed) {
                        PremiumModelTag(
                            onClick = {
                                scope.launch {
                                    // 如果是已经删除的agent，则不可点击，并提示
                                    if (agentInfo?.isDeleted == true) {
                                        ToastUtils.showShort(R.string.str_agent_is_deleted)
                                    } else {
                                        // 如果不是VIP，显示高级模型的弹窗
                                        showPremiumDialog = true
                                    }
                                }
                            },
                        )
                        Spacer(Modifier.height(8.dp))
                        // 高级模型弹窗
                        if (showPremiumDialog) {
                            // 检查是否已登录
                            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                                // 去会员中心
                                VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                            } else {
                                // 如果未登录，要求先登录
                                LoginActivity.launch(context)
                            }
                            showPremiumDialog = false
                        }
                    }

                    // 消息列表区域 - 等待数据加载完成
                    val chatMessages by chatViewModel.msgs.collectAsState()
                    val isLoadingMore by chatViewModel.isLoadingMore.collectAsState()
                    val hasMoreMessages by chatViewModel.hasMoreMessages.collectAsState()
                    val listState = rememberLazyListState()

                    // 计算是否展示"加载更多"区域（仅在真正的 load more 场景出现）
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

                    LazyColumn(
                        modifier = Modifier
                            .weight(1f)
                            .padding(horizontal = 16.dp),
                        state = listState,
                        reverseLayout = true, // ⚠️此处使用了reverse，导致布局列表是反向的
                    ) {
                        item { Spacer(Modifier.height(16.dp)) }
                        // 1. 用户和 agent 的对话消息（显示在底部，因为是反向列表）
                        // 过滤掉 chatMessages 中的开场白消息
                        val filteredChatMessages = chatMessages.filter { !it.isOpening() }
                        // 添加安全检查
                        runCatching {
                            if (filteredChatMessages.isNotEmpty()) {
                                // 创建消息列表的副本以避免并发修改
                                val messagesCopy = filteredChatMessages.toList()
                                val items =
                                    messagesCopy.filter {
                                        // 过滤掉用户continue消息
                                        !(it.role == "user" && it.content == "continue")
                                        // 注意：图片loading消息不过滤，它们会在ChatItem中显示为shimmer占位
                                    }
                                if (items.isNotEmpty()) {
                                    itemsIndexed(
                                        items,
                                        key = { index, info ->
                                            // 使用消息的唯一标识符作为 key，如果没有则使用索引和内容的组合
                                            info.localMsgId.ifEmpty {
                                                "${index}_${info.role}_${info.content.hashCode()}_${index}"
                                            }
                                        },
                                    ) { index, item ->
                                        runCatching {
                                            // 明确数据边界
                                            if (index < items.size) {
                                                // 判断是否为最后一条AI文本消息（在反向列表中，index=0是最后一条）
                                                // 排除loading消息、用户消息和图片消息
                                                // 图片消息：content为空且有generatedImage
                                                val hasGeneratedImage = item.hasGeneratedImage()
                                                val isImageMessage =
                                                    item.content.isEmpty() && hasGeneratedImage
                                                val isLatestAssistantTextMessage =
                                                    index == 0 &&
                                                            item.role == "assistant" &&
                                                            item.content != "loading_animation" &&
                                                            !isImageMessage

                                                ChatItem(
                                                    item,
                                                    isCurrentPage = isCurrentPage,
                                                    chatViewModel = chatViewModel,
                                                    isLatestMessage = isLatestAssistantTextMessage,
                                                )
                                            }
                                            Spacer(Modifier.height(16.dp))
                                        }
                                            .onFailure { e ->
                                                // 渲染失败时显示错误占位符
                                                Box(
                                                    modifier =
                                                        Modifier
                                                            .fillMaxWidth()
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
                                // 如果整个列表渲染失败，显示错误信息
                                item {
                                    Box(
                                        modifier =
                                            Modifier
                                                .fillMaxWidth()
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
                        // 2/3. Agent Intro + Opening（等待getMsgs完成后再显示，仅在无更多分页或完全无消息时展示，位于顶部）
                        // 优化：等待getMsgs完成，并且（没有更多消息 或 消息列表为空）时才显示
                        val showIntroOpeningTop =
                            isQueryMsgsCompleted && ((!hasMoreMessages) || chatMessages.isEmpty())
                        LogUtils.d(
                            "ChatPage: showIntroOpeningTop=$showIntroOpeningTop, isQueryMsgsCompleted=$isQueryMsgsCompleted, hasMoreMessages=$hasMoreMessages, chatMessages.size=${chatMessages.size}"
                        )
                        if (showIntroOpeningTop) {
                            // Opening 消息（带音频自动播放逻辑，ChatItem 内部处理）
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
                            // Intro 卡片优先
                            item {
                                agentInfo?.intro?.let { info ->
                                    if (info.isNotEmpty()) {
                                        AgentInfoChatCard(info)
                                        Spacer(Modifier.height(16.dp))
                                    }
                                }
                            }
                        }

                        // 4. 加载更多指示器（显示在列表顶部，因为是反向布局）
                        if (showLoadMoreUi) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(60.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    if (isLoadingMore) {
                                        CircularProgressIndicator(
                                            color = MaterialTheme.colorScheme.primary,
                                            modifier = Modifier
                                                .width(24.dp)
                                                .height(24.dp),
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

                    // 监听滚动状态，实现智能加载更多
                    LaunchedEffect(hasMoreMessages, isLoadingMore, chatMessages.size) {
                        // 使用 snapshotFlow 持续监听滚动状态变化
                        snapshotFlow {
                            listState.firstVisibleItemIndex to
                                    listState.firstVisibleItemScrollOffset
                        }.collect { (firstVisibleIndex, scrollOffset) ->
                            // 添加小延迟，确保首次加载完成后再开始监听
                            delay(100)
                            val layoutInfo = listState.layoutInfo
                            val visibleItems = layoutInfo.visibleItemsInfo
                            val totalItemsCount = layoutInfo.totalItemsCount
                            val lastVisibleIndex = visibleItems.maxOfOrNull { it.index } ?: 0

                            // 智能触发条件：
                            // 1. 必须有足够的数据（超过一屏，即超过可见项目数）
                            // 2. 在反向布局中，当滚动到接近顶部时触发
                            // 3. 确保还有更多消息可加载
                            // 4. 避免在数据量不足时误触发
                            val hasEnoughData =
                                totalItemsCount > visibleItems.size + LOAD_MORE_MIN_EXTRA_ITEMS
                            // 反向布局：接近顶部意味着可见的最大index接近总items末尾
                            val isNearTop =
                                totalItemsCount > 0 &&
                                        lastVisibleIndex >=
                                        (totalItemsCount - LOAD_MORE_NEAR_TOP_THRESHOLD)
                            // 在反向布局中，firstVisibleItemIndex=0表示在底部（最新消息），需要滚动到更早的消息才算滚动过
                            val hasScrolled = firstVisibleIndex > 0 || scrollOffset > 0
                            val shouldLoadMore = hasEnoughData && isNearTop && hasScrolled

                            if (shouldLoadMore && hasMoreMessages && !isLoadingMore) {
                                LogUtils.i("Triggering smart load more messages")
                                chatViewModel.loadMoreMessages()
                            }
                        }
                    }

                    // 输入框区域
                    // 如果是已经删除的agent，则不可点击，并提示
                    if (agentInfo?.isDeleted == true) {
                        Box(
                            modifier =
                                Modifier
                                    .fillMaxWidth()
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

                // Keep talking悬浮按钮 - 放在最外层Box，相对整个页面定位，在ChatInput上方，右侧对齐屏幕
                // Keep talking按钮显示条件：设置开启 && 有最后一条AI消息 && 是真实消息（不能是intro或opening）
                // 判断是否有最后一条AI文本消息（用于显示keep talking按钮）
                // 注意：chatMessages是反向列表，第一个元素是最后一条消息
                // 直接计算，不使用 remember，确保每次消息列表变化时都会重新计算
                val chatMessagesForButton by chatViewModel.msgs.collectAsState()
                val hasLatestAssistantMessage =
                    chatMessagesForButton.firstOrNull()?.let { firstMsg ->
                        val hasGeneratedImage = firstMsg.hasGeneratedImage()
                        val isImageMessage = firstMsg.content.isEmpty() && hasGeneratedImage
                        // 判断条件：
                        // 1. 必须是 assistant 消息
                        // 2. 不能是 loading 占位
                        // 3. 不能是纯图片消息
                        // 4. 不能是 opening 消息（真实消息，不是intro或opening）
                        firstMsg.role == "assistant" &&
                                firstMsg.content != "loading_animation" &&
                                !isImageMessage &&
                                !firstMsg.isOpening()
                    } ?: false
                val showKeepTalkingButton = shouldShowButton && hasLatestAssistantMessage

                val chatInputEstimatedHeight = 70.dp
                val effectiveBottomPaddingForButton =
                    if (showMorePanel) morePanelHeight else bottomPadding
                // 键盘高度：键盘弹出时，按钮需要向上移动键盘高度
                // 注意：在 ChatActivity（showBackButton = true）中，外部已经应用了 .imePadding()，
                // 内部 Column 也应用了 .imePadding()，所以按钮计算时不应该再加 imeHeightDp，
                // 否则会导致向上偏移两个键盘的 padding 距离
                // 在 HorizontalPager 中（showBackButton = false），外部没有 .imePadding()，
                // 只有内部 Column 的 .imePadding()，所以按钮计算时需要加 imeHeightDp
                val imeHeightDp = with(LocalDensity.current) { imeHeight.toDp() }
                val buttonBottomOffset = if (showBackButton) {
                    // ChatActivity：外部和内部都应用了 .imePadding()，不需要再加键盘高度
                    chatInputEstimatedHeight + effectiveBottomPaddingForButton
                } else {
                    // HorizontalPager：只有内部 Column 应用了 .imePadding()，需要再加键盘高度
                    chatInputEstimatedHeight + effectiveBottomPaddingForButton + imeHeightDp
                }

                KeepTalkingFloatingButton(
                    visible = showKeepTalkingButton,
                    onClick = { chatViewModel.sendKeepTalkingMessage() },
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(bottom = buttonBottomOffset) // 在输入框上方，右侧对齐屏幕，随键盘向上平移
                )
            }
        }

        // MorePanel
        ChatMorePanel(
            visible = showMorePanel,
            agentInfo = agentInfo,
            chatViewModel = chatViewModel,
            onDismiss = { showMorePanel = false },
            onHeightChange = { h -> morePanelHeight = h },
        )

        // 聊天设置抽屉
        ChatSettingsDrawer(
            chatViewModel = chatViewModel,
            agentInfo = agentInfo,
            drawerState = drawerState,
            onKeepTalkingChange = { enabled -> onKeepTalkingChange(enabled) },
        )

        // 免费聊天次数限制的dialog
        ShowLimitDialog(chatViewModel)

        // 图片生成错误弹窗
        ShowImageGenerationDialog(chatViewModel)

        // 监听需要登录事件并跳转
        val needLogin by chatViewModel.requestLogin.collectAsState()
        if (needLogin) {
            // 如果未登录或为游客，则跳转登录
            LoginActivity.launch(context)
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
            // 等待一次帧同步，确保TextField已附着焦点请求者
            delay(50)
            inputFocusRequester.requestFocus()
        } else {
            suppressFocusCallback.value = true
            focusManager.clearFocus()
        }
    }
}

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
                // 检查是否已登录
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    // 去会员中心
                    VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                } else {
                    // 如果未登录，要求先登录
                    LoginActivity.launch(context)
                }
                chatViewModel.dismissDialog()
            },
            onMoreInfo = {
                // 检查是否已登录
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    // 去会员中心
                    VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                } else {
                    // 如果未登录，要求先登录
                    LoginActivity.launch(context)
                }
                chatViewModel.dismissDialog()
            },
        )
    }
}

@Composable
private fun ShowImageGenerationDialog(chatViewModel: ChatViewModel) {
    val context = LocalContext.current
    val dialogData by chatViewModel.showImageGenerationDialog.collectAsState()

    dialogData?.let { data ->
        val content = when (data.errorType) {
            ChatViewModel.ImageGenerationErrorType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                stringResource(R.string.image_generation_free_limit_content)
            }

            ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {
                stringResource(R.string.image_generation_vip_limit_content)
            }
        }

        val dialogDataForUI = ChatDialogData(
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
                        // 免费用户：去会员中心
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                        } else {
                            LoginActivity.launch(context)
                        }
                    }

                    ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {
                        // 会员用户：只是提示，关闭弹窗即可
                    }
                }
                chatViewModel.dismissImageGenerationDialog()
            },
            onMoreInfo = {
                when (data.errorType) {
                    ChatViewModel.ImageGenerationErrorType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                        // 免费用户：去会员中心
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            VipCenterActivity.launch(context, VipCenterActivity.CHAT_PAGE)
                        } else {
                            LoginActivity.launch(context)
                        }
                    }

                    ChatViewModel.ImageGenerationErrorType.VIP_USER_LIMIT_REACHED -> {
                        // 会员用户：只是提示，关闭弹窗即可
                    }
                }
                chatViewModel.dismissImageGenerationDialog()
            },
        )
    }
}
