package com.ai.inty.chat

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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.ToastUtils
import com.ai.inty.beans.MsgInfo
import com.ai.inty.billing.BillingRepository
import com.ai.inty.chat.ui.ChatInput
import com.ai.inty.chat.ui.ChatMorePanel
import com.ai.inty.chat.ui.ChatSettingsDrawer
import com.ai.inty.chat.ui.ChatTopBar
import com.ai.inty.chat.ui.KeepTalkingButton
import com.ai.inty.home.BottomNavigationBarHeight
import com.ai.inty.ui.ChatDialogData
import com.ai.inty.ui.UnlimitChatDialog
import com.ai.inty.ui.components.AgentBackground
import com.ai.inty.utils.TrackScreenView
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.launch

// The spacer from the bottom of the chat input to what ever that flows underneath it.
val ChatInputBottomSpacerHeight = 8.dp
private const val LOAD_MORE_NEAR_TOP_THRESHOLD = 3
private const val LOAD_MORE_MIN_EXTRA_ITEMS = 5

@Composable
internal fun ChatPage(
    modifier: Modifier,
    chatViewModel: ChatViewModel,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
    isCurrentPage: Boolean = true,
) {

    val context = LocalContext.current
    val agentInfo by chatViewModel.agentInfo.collectAsState()

    // 跟踪ChatPage页面访问
    TrackScreenView(
        screenName = "ChatPage",
        screenClass = if (showBackButton) "ChatActivity" else "MainActivity",
        additionalParams =
            mapOf(
                "agent_id" to (agentInfo?.id ?: "unknown"),
                "agent_name" to (agentInfo?.name ?: "unknown"),
                "show_back_button" to showBackButton,
            ),
    )

    LaunchedEffect(chatViewModel) {
        chatViewModel.queryMsgs()
        // 初始化语音服务
        chatViewModel.initVoiceService(context)
    }

    // 统一生命周期：页面进入 onPause（包括 Activity 或应用退到后台）时停止音频
    LifecycleResumeEffect(isCurrentPage) {
        onPauseOrDispose {
            EasyLog.log("音频LOG测试 ChatPage onPause -> stopAllPlayback")
            chatViewModel.pauseVoicePlayback()
        }
    }

    // 页面生命周期管理：离开页面时重置播放状态
    DisposableEffect(chatViewModel, isCurrentPage) {
        onDispose {
            if (!isCurrentPage) {
                EasyLog.log("音频LOG测试 ChatPage disposed, resetting voice playback")
                chatViewModel.resetVoicePlayback()
                // 清理OpeningPlayState中可能存在的错误状态
                agentInfo?.id?.let { agentId ->
                    // 注意：这里不清理已播放状态，因为用户可能希望保持已播放记录
                    // 只在应用重启时清理，通过OpeningPlayState的clearAllPlayed方法
                    EasyLog.log("音频LOG测试 ChatPage disposed for agent: $agentId")
                }
            }
        }
    }

    // 监听agent变化，当agent切换时停止非当前agent的播放
    LaunchedEffect(agentInfo?.id) {
        val currentAgentId = agentInfo?.id
        if (currentAgentId != null) {
            // 当agent切换时，停止非当前agent的音频播放
            chatViewModel.stopNonCurrentAgentPlayback()
            EasyLog.log("Agent切换，停止非当前agent的音频播放: $currentAgentId")
        }
    }

    val density = LocalDensity.current
    val focusManager = LocalFocusManager.current

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

    // Keep talking二状态设置：默认跟随全局设置
    var agentKeepTalking by
        remember(agentInfo?.id) {
            mutableStateOf(
                agentInfo?.let {
                    // 获取角色专用设置，如果不存在则使用全局设置
                    IntySetting.getAgentKeepTalking(it.id) ?: IntySetting.isShowKeepTalking()
                } ?: false
            )
        }

    // 用于实时更新按钮显示状态
    var shouldShowButton by remember(agentInfo?.id) { mutableStateOf(agentKeepTalking) }

    // Keep talking状态变化回调
    fun onKeepTalkingChange(enabled: Boolean) {
        agentKeepTalking = enabled
        shouldShowButton = enabled
    }

    // VIP状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()


    var showMorePanel by remember { mutableStateOf(false) }
    var morePanelHeight by remember { mutableStateOf(0.dp) }

    Box(
        modifier =
            modifier.pointerInput(Unit) { detectTapGestures(onTap = { focusManager.clearFocus() }) }
    ) {
        // 背景
        AgentBackground(agentInfo = agentInfo, showGradients = true)

        val drawerState = remember { mutableStateOf(DrawerValue.Closed) }
        val scope = rememberCoroutineScope()

        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0),
        ) { innerPadding ->
            Column(modifier = Modifier.padding(innerPadding).imePadding()) {
                Spacer(Modifier.height(48.dp))

                agentInfo?.let { info ->
                    ChatTopBar(
                        modifier = Modifier.fillMaxWidth().padding(start = 18.dp),
                        agentInfo = info,
                        showBackButton = showBackButton,
                        onBack = onBack,
                        onClickMore = {
                            scope.launch {
                                // 如果是已经删除的agent，则不可点击，并提示
                                if (agentInfo?.isDeleted == true) {
                                    ToastUtils.showToast(R.string.str_agent_is_deleted)
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

                val chatMessages by chatViewModel.msgs.collectAsState()
                val isLoadingMore by chatViewModel.isLoadingMore.collectAsState()
                val hasMoreMessages by chatViewModel.hasMoreMessages.collectAsState()
                val listState = rememberLazyListState()

                // 计算是否展示“加载更多”区域（仅在真正的 load more 场景出现）
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
                    modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
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
                                        !(it.role == "user" && it.content == "continue")
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
                                                    ChatItem(
                                                        item,
                                                        isCurrentPage = isCurrentPage,
                                                        chatViewModel = chatViewModel,
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
                            // 如果整个列表渲染失败，显示错误信息
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
                    // 2/3. Agent Intro + Opening（仅在无更多分页或完全无消息时展示，位于顶部）
                    val showIntroOpeningTop = (!hasMoreMessages) || chatMessages.isEmpty()
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

                // 监听滚动状态，实现智能加载更多
                LaunchedEffect(hasMoreMessages, isLoadingMore, chatMessages.size) {
                    // 使用 snapshotFlow 持续监听滚动状态变化
                    snapshotFlow {
                            listState.firstVisibleItemIndex to
                                listState.firstVisibleItemScrollOffset
                        }
                        .collect { (firstVisibleIndex, scrollOffset) ->
                            // 添加小延迟，确保首次加载完成后再开始监听
                            kotlinx.coroutines.delay(100)
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

                            EasyLog.log(
                                "Smart scroll check: shouldLoadMore=$shouldLoadMore, hasEnoughData=$hasEnoughData (totalItemsCount=$totalItemsCount > visibleItems=${visibleItems.size}+${LOAD_MORE_MIN_EXTRA_ITEMS}), isNearTop=$isNearTop (lastVisibleIndex=$lastVisibleIndex, threshold=${totalItemsCount - LOAD_MORE_NEAR_TOP_THRESHOLD}), hasScrolled=$hasScrolled (firstVisibleIndex=$firstVisibleIndex, scrollOffset=$scrollOffset), hasMoreMessages=$hasMoreMessages, isLoadingMore=$isLoadingMore"
                            )

                            if (shouldLoadMore && hasMoreMessages && !isLoadingMore) {
                                EasyLog.log("Triggering smart load more messages")
                                chatViewModel.loadMoreMessages()
                            }
                        }
                }

                // 输入框区域
                Column {
                    // 如果是已经删除的agent，则不可点击，并提示
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
                        // Keep talking 按钮
                        KeepTalkingButton(
                            visible = shouldShowButton,
                            onClick = { chatViewModel.sendKeepTalkingMessage() },
                        )
                        // 输入框
                        val effectiveBottomPadding =
                            if (showMorePanel) morePanelHeight else bottomPadding
                        ChatInput(
                            chatViewModel = chatViewModel,
                            onSendMessage = { chatViewModel.sendMsg() },
                            onToggleMorePanel = { showMorePanel = !showMorePanel },
                            showMorePanel = showMorePanel,
                            bottomPadding = effectiveBottomPadding,
                        )
                    }
                }
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

        // 监听需要登录事件并跳转
        val needLogin by chatViewModel.requestLogin.collectAsState()
        if (needLogin) {
            // 如果未登录或为游客，则跳转登录
            TheRouter.build(Constant.ROUTE_LOGIN).navigation(context)
            chatViewModel.dismissLoginRequest()
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
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    // 去会员中心
                    TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                } else {
                    // 如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN).navigation(context)
                }
                chatViewModel.dismissDialog()
            },
            onMoreInfo = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    // 去会员中心
                    TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                } else {
                    // 如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN).navigation(context)
                }
                chatViewModel.dismissDialog()
            },
        )
    }
}
