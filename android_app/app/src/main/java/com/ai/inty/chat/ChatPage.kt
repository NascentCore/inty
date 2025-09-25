package com.ai.inty.chat

import android.app.Activity
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DrawerValue
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
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.ToastUtils
import com.ai.inty.beans.MsgInfo
import com.ai.inty.billing.BillingRepository
import com.ai.inty.home.BottomNavigationBarHeight
import com.ai.inty.ui.AdvancedModelChatDialog
import com.ai.inty.ui.ChatDialogData
import com.ai.inty.ui.UnlimitChatDialog
import com.ai.inty.ui.components.AgentBackground
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.launch


// The spacer from the bottom of the chat input to what ever that flows underneath it.
val ChatInputBottomSpacerHeight = 8.dp

@Composable
internal fun ChatPage(
    modifier: Modifier,
    chatViewModel: ChatViewModel,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
) {

    val context = LocalContext.current

    LaunchedEffect(chatViewModel) {
        chatViewModel.queryMsgs()
        // 初始化语音服务
        chatViewModel.initVoiceService(context)
    }

    // 页面生命周期管理：离开页面时重置播放状态
    DisposableEffect(chatViewModel) {
        onDispose {
            EasyLog.log("ChatPage disposed, resetting voice playback")
            chatViewModel.resetVoicePlayback()
        }
    }

    val density = LocalDensity.current
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val focusManager = LocalFocusManager.current

    // 检测键盘状态
    val imeHeight = WindowInsets.ime.getBottom(density)
    val isKeyboardVisible = imeHeight > 0

    // 动态计算底部间距
    val bottomPadding = when {
        showBackButton -> ChatInputBottomSpacerHeight // 独立聊天页面：固定
        isKeyboardVisible -> ChatInputBottomSpacerHeight // 首页聊天页面，键盘呼出时
        else -> BottomNavigationBarHeight + ChatInputBottomSpacerHeight // 首页聊天页面，无键盘时
    }

    // Keep talking二状态设置：默认跟随全局设置
    var agentKeepTalking by remember(agentInfo?.id) {
        mutableStateOf(
            agentInfo?.let {
                // 获取角色专用设置，如果不存在则使用全局设置
                IntySetting.getAgentKeepTalking(it.id) ?: IntySetting.isShowKeepTalking()
            } ?: false
        )
    }

    // 用于实时更新按钮显示状态
    var shouldShowButton by remember(agentInfo?.id) { mutableStateOf(agentKeepTalking) }

    // VIP状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    // Premium model二状态设置：默认跟随全局设置，但受VIP状态限制
    var agentPremiumModel by remember(agentInfo?.id, vipStatus.isSubscribed) {
        mutableStateOf(
            if (!vipStatus.isSubscribed) {
                // 如果不是VIP，强制关闭Premium model
                false
            } else {
                agentInfo?.let {
                    // 获取角色专用设置，如果不存在则使用全局设置
                    IntySetting.getAgentPremiumModel(it.id) ?: IntySetting.isShowPremiumModel()
                } ?: false
            }
        )
    }

    var showMorePanel by remember { mutableStateOf(false) }
    var showPremiumDialog by remember { mutableStateOf(false) }

    Box(
        modifier = modifier
            .pointerInput(Unit) {
                detectTapGestures(
                    onTap = {
                        focusManager.clearFocus()
                    }
                )
            }
    ) {
        // 背景
        AgentBackground(
            agentInfo = agentInfo,
            showGradients = true
        )

        val drawerState = remember { mutableStateOf(DrawerValue.Closed) }
        val scope = rememberCoroutineScope()

        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0),
        ) { innerPadding ->

            Column(
                modifier = Modifier
                    .padding(innerPadding)
                    .imePadding()
            ) {
                Spacer(Modifier.height(48.dp))

                agentInfo?.let { info ->
                    ChatTopBar(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 18.dp, vertical = 0.dp),
                        agentInfo = info,
                        showBackButton = showBackButton,
                        onBack = onBack,
                        onClickMore = {
                            scope.launch {
                                //如果是已经删除的agent，则不可点击，并提示
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

                // Premium model标签
                if (agentInfo != null) {
                    PremiumModelTag(
                        isPremiumModel = agentPremiumModel,
                        onClick = {
                            scope.launch {
                                //如果是已经删除的agent，则不可点击，并提示
                                if (agentInfo?.isDeleted == true) {
                                    ToastUtils.showToast(R.string.str_agent_is_deleted)
                                } else {
                                    // 检查VIP状态
                                    if (!vipStatus.isSubscribed) {
                                        // 如果不是VIP，显示高级模型的弹窗
                                        showPremiumDialog = true
                                    } else {
                                        // 如果是VIP，打开聊天设置抽屉，让用户手动设置开关
                                        if (drawerState.value == DrawerValue.Closed) {
                                            drawerState.value = DrawerValue.Open
                                        } else {
                                            drawerState.value = DrawerValue.Closed
                                        }
                                    }
                                }
                            }

                        }
                    )
                    Spacer(Modifier.height(8.dp))
                    // 高级模型弹窗
                    if (showPremiumDialog) {
                        val data = ChatDialogData(
                            R.drawable.img_advanced_model_dialog_bg,
                            stringResource(R.string.str_premium_mode_dialog_content),
                            stringResource(R.string.settings_premium_model)
                        )
                        AdvancedModelChatDialog(
                            data,
                            onCancel = { showPremiumDialog = false },
                            onSure = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    if (context is Activity) {
                                        // 购买最低档位的订阅
                                        chatViewModel.purchaseFirstVip(context)
                                    }
                                } else {
                                    //如果未登录，要求先登录
                                    TheRouter.build(Constant.ROUTE_LOGIN)
                                        .navigation(context)
                                }
                                showPremiumDialog = false

                            },
                            onMoreInfo = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    // 去会员中心
                                    TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                                } else {
                                    //如果未登录，要求先登录
                                    TheRouter.build(Constant.ROUTE_LOGIN)
                                        .navigation(context)
                                }
                                showPremiumDialog = false
                            }
                        )
                    }
                }
                val chatMessages by chatViewModel.msgs.collectAsState()
                EasyLog.log("=== LazyColumn 渲染开始 ===")
                EasyLog.log("Chat Messages State: ${chatMessages.size} 条消息")
                EasyLog.log("Agent Info State: ${agentInfo?.id ?: "null"}")
                
                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .padding(horizontal = 16.dp),
                    reverseLayout = true,//⚠️此处使用了reverse，导致布局列表是反向的
                ) {
                    item {
                        Spacer(Modifier.height(16.dp))
                    }
                    
                    // 1. Agent Intro (显示在最上面，因为是反向列表)
                    item {
                        agentInfo?.intro?.let { info ->
                            if (info.isNotEmpty()) {
                                EasyLog.log("=== 显示 Agent Intro ===")
                                AgentInfoChatCard(info)
                            }
                        }
                    }
                    
                    // 2. Agent Opening (显示在 Agent Intro 之后)
                    item {
                        agentInfo?.let { agent ->
                            EasyLog.log("=== 开场白显示检查 ===")
                            EasyLog.log("Agent ID: ${agent.id}")
                            EasyLog.log("Agent Name: ${agent.name}")
                            EasyLog.log("Agent Opening: '${agent.opening}'")
                            EasyLog.log("Agent Opening Length: ${agent.opening.length}")
                            EasyLog.log("Agent Opening Audio URL: '${agent.opening_audio_url}'")
                            
                            // 始终显示开场白
                            val shouldShowOpening = agent.opening.isNotEmpty()
                            EasyLog.log("Should Show Opening: $shouldShowOpening (always show if agent has opening)")
                            
                            if (shouldShowOpening) {
                                EasyLog.log("=== 创建开场白消息 ===")
                                // 创建开场白消息
                                val openingMessage = MsgInfo(
                                    content = agent.opening,
                                    role = "assistant",
                                    meta_data = MsgInfo.MsgMetaData(
                                        agentId = agent.id,
                                        isOpening = true
                                    ),
                                    audio_url = agent.opening_audio_url
                                )
                                EasyLog.log("Opening Message Created: $openingMessage")
                                EasyLog.log("Opening Message Content: '${openingMessage.content}'")
                                EasyLog.log("Opening Message Role: '${openingMessage.role}'")
                                EasyLog.log("Opening Message Audio URL: '${openingMessage.audio_url}'")
                                EasyLog.log("Opening Message Meta Data: ${openingMessage.meta_data}")
                                EasyLog.log("Opening Message Is Opening: ${openingMessage.isOpening()}")
                                
                                ChatItem(openingMessage)
                                Spacer(Modifier.height(16.dp))
                                EasyLog.log("=== 开场白消息已渲染 ===")
                            } else {
                                EasyLog.log("=== 不显示开场白 ===")
                                EasyLog.log("原因: Agent opening 为空")
                            }
                        } ?: run {
                            EasyLog.log("=== Agent Info 为空 ===")
                        }
                    }

                    // 3. 用户和 agent 的对话消息
                    // 过滤掉 chatMessages 中的开场白消息
                    val filteredChatMessages = chatMessages.filter { !it.isOpening() }
                    EasyLog.log("=== 消息过滤 ===")
                    EasyLog.log("原始消息数量: ${chatMessages.size}")
                    EasyLog.log("过滤后消息数量: ${filteredChatMessages.size}")
                    chatMessages.forEachIndexed { index, msg ->
                        EasyLog.log("消息 $index: role='${msg.role}', isOpening=${msg.isOpening()}, content='${msg.content.take(50)}...'")
                    }

                    // 添加安全检查
                    runCatching {
                        if (filteredChatMessages.isNotEmpty()) {
                            // 创建消息列表的副本以避免并发修改
                            val messagesCopy = filteredChatMessages.toList()
                            val items =
                                messagesCopy.filter { !(it.role == "user" && it.content == "continue") }
                            if (items.isNotEmpty()) {
                                itemsIndexed(
                                    items,
                                    key = { index, info ->
                                        // 使用消息的唯一标识符作为 key，如果没有则使用索引和内容的组合
                                        info.localMsgId.ifEmpty { "${index}_${info.role}_${info.content.hashCode()}_${index}" }
                                    }
                                ) { index, item ->
                                    runCatching {
                                        //明确数据边界
                                        if (index < items.size) {
                                            ChatItem(item)
                                        }
                                        Spacer(Modifier.height(16.dp))
                                    }.onFailure { e ->
                                        EasyLog.log(
                                            "Error rendering chat item at index $index: ${e.message}",
                                            priority = EasyLog.ERROR
                                        )
                                        // 渲染失败时显示错误占位符
                                        Box(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .height(60.dp)
                                                .background(Color.Red.copy(alpha = 0.1f))
                                        ) {
                                            Text(
                                                text = "Message loading failed",
                                                color = Color.White,
                                                modifier = Modifier.align(Alignment.Center)
                                            )
                                        }
                                        Spacer(Modifier.height(16.dp))
                                    }
                                }
                            }
                        }
                    }.onFailure { e ->
                        EasyLog.log("Error in LazyColumn: ${e.message}", priority = EasyLog.ERROR)
                        // 如果整个列表渲染失败，显示错误信息
                        item {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(100.dp)
                                    .background(Color.Red.copy(alpha = 0.1f))
                            ) {
                                Text(
                                    text = "Chat history loading failed, please retry",
                                    color = Color.White,
                                    modifier = Modifier.align(Alignment.Center)
                                )
                            }
                        }
                    }
                }

                // 输入框区域
                Column {
                    //如果是已经删除的agent，则不可点击，并提示
                    if (agentInfo?.isDeleted == true) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp)
                                .padding(horizontal = 16.dp)
                                .clip(RoundedCornerShape(24.dp))
                                .background(Color(0x9937303D)),
                            contentAlignment = Alignment.Center
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
                            onClick = { chatViewModel.sendKeepTalkingMessage() }
                        )
                        // 输入框
                        ChatInput(
                            chatViewModel = chatViewModel,
                            onSendMessage = { chatViewModel.sendMsg() },
                            onToggleMorePanel = { showMorePanel = !showMorePanel },
                            showMorePanel = showMorePanel,
                            bottomPadding = bottomPadding
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
            onDismiss = { showMorePanel = false }
        )

        // 聊天设置抽屉
        ChatSettingsDrawer(
            chatViewModel = chatViewModel,
            agentInfo = agentInfo,
            drawerState = drawerState,
            onPremiumDialogShow = { show -> showPremiumDialog = show },
            onPremiumModeChange = { mode -> agentPremiumModel = mode }
        )

        //免费聊天次数限制的dialog
        ShowLimitDialog(chatViewModel)

    }
}

@Composable
private fun ShowLimitDialog(chatViewModel: ChatViewModel) {
    val showDialog by chatViewModel.showLimitDialog.collectAsState()
    val context = LocalContext.current
    if (showDialog) {
        val data = ChatDialogData(
            R.drawable.img_unlimit_dialog_bg,
            stringResource(R.string.str_unlimit_dialog_content),
            stringResource(R.string.str_unlimit_btn_text)
        )
        UnlimitChatDialog(
            data,
            onCancel = {
                chatViewModel.dismissDialog()
            },
            onSure = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    if (context is Activity) {
                        //最低档位购买会员订阅
                        chatViewModel.purchaseFirstVip(context)
                    }
                } else {
                    //如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN)
                        .navigation(context)
                }
                chatViewModel.dismissDialog()
            },
            onMoreInfo = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    // 去会员中心
                    TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                } else {
                    //如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN)
                        .navigation(context)
                }
                chatViewModel.dismissDialog()
            },
        )
    }
}
