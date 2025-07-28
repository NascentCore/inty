package com.ai.inty.chat

//import com.ai.inty.billing.BillingRepository
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.BottomSheetDialog
import com.ai.inty.base.DiaAmountLayout
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.IntySmallTextField
import com.ai.inty.base.MyModalNavigationDrawer
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.MsgInfo
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.utils.getChatBackground
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

@Composable
internal fun ChatPage(
    modifier: Modifier,
    chatViewModel: ChatViewModel,
    onFollowAgent: ((String) -> Unit)? = null,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
) {
    LifecycleResumeEffect(chatViewModel) {
        chatViewModel.queryMsgs()
        onPauseOrDispose { }
    }

    val context = LocalContext.current
    val density = LocalDensity.current
    val agentInfo = chatViewModel.agentInfo.collectAsState().value
    val focusManager = LocalFocusManager.current

    // 获取字符串资源
    val youAreNotVipText = stringResource(R.string.you_are_not_vip)
    val premiumModelText = stringResource(R.string.settings_premium_model)

    // 检测键盘状态
    val imeHeight = WindowInsets.ime.getBottom(density)
    val isKeyboardVisible = imeHeight > 0

    // 动态计算底部间距
    val bottomPadding = when {
        showBackButton -> 10.dp // 独立聊天页面：固定10dp
        isKeyboardVisible -> 10.dp // 首页聊天页面，键盘呼出时：10dp
        else -> 90.dp // 首页聊天页面，无键盘时：90dp（给底部tab留出更多间隔）
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
    var shouldShowButton by remember(agentInfo?.id) {
        mutableStateOf(agentKeepTalking)
    }
    /*
        // VIP状态
        val vipStatus = BillingRepository.vipStatusFlow.collectAsState().value

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
        }*/

    var showMorePanel by remember { mutableStateOf(false) }



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
        val configuration = LocalConfiguration.current

        var imageWidthDp by remember {
            mutableIntStateOf(configuration.screenWidthDp)
        }
        var imageHeightDp by remember {
            mutableIntStateOf(configuration.screenHeightDp)
        }
        if (configuration.screenWidthDp > imageWidthDp) {
            imageWidthDp = configuration.screenWidthDp
        }
        if (configuration.screenHeightDp > imageHeightDp) {
            imageHeightDp = configuration.screenHeightDp
        }
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState(), false)
                .onSizeChanged {
                    val newHeight = with(density) {
                        it.height.toDp().value.roundToInt()
                    }
                    if (newHeight > imageHeightDp) {
                        imageHeightDp = newHeight
                    }
                }
        ) {
            IntyImage(
                modifier = Modifier
                    .size(imageWidthDp.dp, imageHeightDp.dp),
                model = agentInfo?.getChatBackground(),
                alignment = Alignment.TopCenter,
                contentScale = ContentScale.Crop,
            )
        }

        // 顶部渐变遮罩 - 固定位置
        val colors = listOf(
            Color(0xFF000000),
            Color(0x00000000)
        )
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(120.dp)
                .background(
                    brush = Brush.verticalGradient(colors),
                )
        )
        // 底部渐变遮罩 - 固定位置
        val bottomColors = listOf(
            Color(0x001C1523),
            Color(0xFF1C1523)
        )
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(300.dp)
                .background(
                    brush = Brush.verticalGradient(bottomColors),
                )
                .align(Alignment.BottomCenter)
        )

        val drawerState = remember {
            mutableStateOf(DrawerValue.Closed)
        }
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

                if (agentInfo != null) {
                    TopBar(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(36.dp)
                            .padding(horizontal = 18.dp, vertical = 0.dp),
                        agentInfo = agentInfo,
                        showBackButton = showBackButton,
                        onBack = onBack,
                        onClickMore = {
                            scope.launch {
                                if (drawerState.value == DrawerValue.Closed) {
                                    drawerState.value = DrawerValue.Open
                                } else {
                                    drawerState.value = DrawerValue.Closed
                                }
                            }
                        },
                        onFollowAgent = onFollowAgent
                    )
                }

                Spacer(Modifier.height(16.dp))

                // Premium model标签 - 左上角
                /*if (agentInfo != null) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 18.dp),
                        horizontalArrangement = Arrangement.Start
                    ) {
                        Box(
                            modifier = Modifier
                                .height(32.dp)
                                .background(
                                    brush = if (agentPremiumModel) {
                                        // 激活状态：渐变背景
                                        Brush.horizontalGradient(
                                            colors = listOf(
                                                Color(0xFF2196F3), // 更鲜艳的蓝色
                                                Color(0xFFE91E63)  // 粉色
                                            )
                                        )
                                    } else {
                                        // 置灰状态：半透明灰色
                                        Brush.verticalGradient(
                                            colors = listOf(
                                                Color.Gray.copy(alpha = 0.7f),
                                                Color.Gray.copy(alpha = 0.7f)
                                            )
                                        )
                                    },
                                    shape = RoundedCornerShape(16.dp)
                                )
                                .padding(horizontal = 12.dp)
                                .noRippleClickable {
                                    // 检查VIP状态
                                    if (!vipStatus.isSubscribed) {
                                        // 如果不是VIP，显示提示
                                        Toast.makeText(
                                            context,
                                            youAreNotVipText,
                                            Toast.LENGTH_SHORT
                                        ).show()
                                    } else {
                                        // 如果是VIP，打开聊天设置抽屉
                                        scope.launch {
                                            if (drawerState.value == DrawerValue.Closed) {
                                                drawerState.value = DrawerValue.Open
                                            } else {
                                                drawerState.value = DrawerValue.Closed
                                            }
                                        }
                                    }
                                },
                            contentAlignment = Alignment.Center
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                // V图标
                                Text(
                                    text = "V",
                                    color = Color.White,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )

                                // Premium model文本
                                Text(
                                    text = premiumModelText,
                                    color = Color.White,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                }*/

                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .padding(horizontal = 16.dp),
                    reverseLayout = true,
                ) {
                    val msgs = chatViewModel.msgs
                    EasyLog.log(" 测试，， msgs count = ${msgs.size}", 4)
                    item {
                        Spacer(Modifier.height(16.dp))
                    }
                    itemsIndexed(msgs.filter { !(it.role == "user" && it.content == "continue") }) { index, item ->
                        ChatItem(item)
                        Spacer(Modifier.height(16.dp))
                    }
                }

                // 输入框区域 - 受键盘影响会向上推，但可以动态向下偏移
                Column {
                    // Keep talking 按钮 - 放在输入框左上方
                    if (shouldShowButton) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp),
                            horizontalArrangement = androidx.compose.foundation.layout.Arrangement.Start
                        ) {
                            Box(
                                modifier = Modifier
                                    .width(80.dp)
                                    .height(32.dp)
                                    .background(
                                        Color.Transparent,
                                        RoundedCornerShape(16.dp)
                                    )
                                    .noRippleClickable {
                                        chatViewModel.sendKeepTalkingMessage()
                                    },
                                contentAlignment = Alignment.Center
                            ) {
                                // 播放按钮图标 (>>)
                                Row(
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = "▶",
                                        color = Color.White,
                                        fontSize = 12.sp
                                    )
                                    Spacer(modifier = Modifier.width(0.dp))
                                    Text(
                                        text = "▶",
                                        color = Color.White,
                                        fontSize = 12.sp
                                    )
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(0.dp))
                    }

                    // 输入框 - 动态底部间距
                    val inputData = chatViewModel.inputData.collectAsState()
                    val isInputFocused = remember { mutableStateOf(false) }

                    Column(
                        modifier = Modifier
                            .padding(
                                start = 16.dp,
                                top = 16.dp,
                                end = 16.dp,
                                bottom = bottomPadding
                            )
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(24.dp))
                            .background(Color(0x9937303D))
                            .clickable(enabled = IntySetting.needBlockInput()) {
                                //游客 未登录的用户，需要弹出年龄段选择，18岁以下的，不让输入。
                                TheRouter.build(Constant.ROUTE_REG_INFO).navigation(context)
                            }
                    ) {
                        // 主输入区域
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(if (isInputFocused.value) 80.dp else 64.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            val inputSelection = chatViewModel.inputSelection.collectAsState()
                            IntySmallTextField(
                                modifier = Modifier.weight(1f),
                                enabled = IntySetting.needBlockInput().not(),
                                value = inputData.value,
                                singleLine = false,
                                onValueChange = {
                                    chatViewModel.inputData.value = it
                                },
                                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Default),
                                keyboardActions = KeyboardActions(),
                                onFocusChanged = { focused ->
                                    isInputFocused.value = focused
                                },
                                onSelectionChanged = { selection ->
                                    chatViewModel.inputSelection.value = selection
                                },
                                selection = inputSelection.value
                            )

                            // 括号按钮区域 - 仅在输入框获得焦点时显示
                            if (isInputFocused.value) {
                                Box(
                                    modifier = Modifier
                                        .width(40.dp)
                                        .height(32.dp)
                                        .background(
                                            Color.White.copy(alpha = 0.1f),
                                            RoundedCornerShape(16.dp)
                                        )
                                        .noRippleClickable {
                                            // 获取当前光标位置
                                            val currentText = inputData.value
                                            val currentSelection =
                                                chatViewModel.inputSelection.value

                                            // 确保光标位置在有效范围内
                                            val safeSelection =
                                                currentSelection.coerceIn(0, currentText.length)

                                            // 在光标位置插入一对括号
                                            val beforeCursor =
                                                currentText.substring(0, safeSelection)
                                            val afterCursor = currentText.substring(safeSelection)
                                            val newText = "$beforeCursor（）$afterCursor"

                                            // 更新文本
                                            chatViewModel.inputData.value = newText

                                            // 设置光标位置到括号中间
                                            val newCursorPosition = safeSelection + 1
                                            chatViewModel.inputSelection.value = newCursorPosition
                                        },
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = "()",
                                        color = Color.White,
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Medium
                                    )
                                }
                            }
                            //有输入内容时，发送按钮显示
                            if (inputData.value.isNotEmpty()) {
                                IntyImage(
                                    modifier = Modifier
                                        .padding(horizontal = 16.dp)
                                        .size(24.dp)
                                        .noRippleClickable {
                                            chatViewModel.sendMsg()
                                        },
                                    model = R.drawable.btn_send
                                )
                            } else {
                                IntyImage(
                                    modifier = Modifier
                                        .padding(horizontal = 16.dp)
                                        .size(24.dp)
                                        .noRippleClickable {
                                            showMorePanel = !showMorePanel
                                        },
                                    model = if (showMorePanel) R.drawable.btn_down else R.drawable.btn_add2
                                )
                            }
                        }
                    }
                }

            }
        }

        // MorePanel - 独立于Scaffold，不受键盘影响
        if (showMorePanel) {
            Dialog(
                onDismissRequest = {
                    showMorePanel = false
                },
                properties = DialogProperties(
                    usePlatformDefaultWidth = false
                )
            ) {
                DiaAmountLayout {
                    SetDiaAmount(0f)
                    BottomSheetDialog(
                        modifier = Modifier,
                        visible = true,
                        onDismissRequest = {
                            showMorePanel = false
                        }
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(
                                    color = BackGround
                                )
                        ) {
                            Spacer(Modifier.width(16.dp))
                            MorePanelItem(
                                icon = R.drawable.icon_report,
                                text = "Report",
                                onClick = {
                                    // 检查是否正式登录（非游客且已登录）
                                    if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                        TheRouter.build(Constant.ROUTE_REPORT)
                                            .withString("targetID", agentInfo?.id)
                                            .withString("targetType", "AGENT")
                                            .navigation(context)
                                    } else {
                                        // 未登录或游客时跳转到登录页面
                                        TheRouter.build(Constant.ROUTE_LOGIN)
                                            .navigation(context)
                                    }
                                }
                            )
                            Spacer(Modifier.width(16.dp))
                        }
                    }
                }
            }
        }
        //聊天设置 右侧菜单
        LifecycleResumeEffect(chatViewModel) {
            chatViewModel.updateUserInfo()
            onPauseOrDispose { }
        }
        MyModalNavigationDrawer(
            modifier = Modifier,
            drawerState = drawerState,
            drawerContent = {
                Column(
                    modifier = Modifier
                        .width(319.dp)
                        .fillMaxHeight()
                        .background(
                            brush = Brush.verticalGradient(
                                colors = listOf(
                                    Color(0xFF322341),
                                    Color(0xFF120E24)
                                )
                            )
                        )
                ) {
                    Text(
                        text = "My Chat Persona",
                        modifier = Modifier.padding(top = 58.dp, start = 16.dp),
                        fontSize = 20.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )

                    Spacer(Modifier.height(14.dp))

                    Column(
                        modifier = Modifier
                            .padding(horizontal = 16.dp)
                            .fillMaxWidth()
                            .border(
                                brush = Brush.linearGradient(
                                    colors = listOf(
                                        Color.Transparent,
                                        Color.White.copy(0.2f),
                                        Color.Transparent
                                    )
                                ),
                                width = 1.dp,
                                shape = RoundedCornerShape(8.dp)
                            )
                            .background(
                                color = Color(0x3378599A),
                                shape = RoundedCornerShape(8.dp)
                            )
                    ) {
                        val userProfile = chatViewModel.userProfile.collectAsState()
                        com.ai.inty.MySettingItem(
                            key = "Name",
                            value = userProfile.value.nickname,
                            onClick = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    TheRouter.build(Constant.ROUTE_SETTING_MY)
                                        .withObject("userProfile", userProfile.value)
                                        .navigation(context)
                                } else {
                                    // 未登录或游客时跳转到登录页面
                                    TheRouter.build(Constant.ROUTE_LOGIN)
                                        .navigation(context)
                                }
                            }
                        )
                        com.ai.inty.MySettingItem(
                            key = "My Pronoun",
                            value = userProfile.value.pronouns(),
                            onClick = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    TheRouter.build(Constant.ROUTE_SETTING_MY)
                                        .withObject("userProfile", userProfile.value)
                                        .navigation(context)
                                } else {
                                    // 未登录或游客时跳转到登录页面
                                    TheRouter.build(Constant.ROUTE_LOGIN)
                                        .navigation(context)
                                }
                            }
                        )
                        com.ai.inty.MySettingItem(
                            key = "My Persona",
                            value = "Edit",
                            onClick = {
                                // 检查是否正式登录（非游客且已登录）
                                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                    TheRouter.build(Constant.ROUTE_SETTING_MY)
                                        .withObject("userProfile", userProfile.value)
                                        .navigation(context)
                                } else {
                                    // 未登录或游客时跳转到登录页面
                                    TheRouter.build(Constant.ROUTE_LOGIN)
                                        .navigation(context)
                                }
                            }
                        )
                    }


                    Spacer(Modifier.height(30.dp))

                    Text(
                        text = "Chat Settings",
                        modifier = Modifier.padding(start = 16.dp),
                        fontSize = 20.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )

                    Spacer(Modifier.height(14.dp))

                    Column(
                        modifier = Modifier
                            .padding(horizontal = 16.dp)
                            .fillMaxWidth()
                            .border(
                                brush = Brush.linearGradient(
                                    colors = listOf(
                                        Color.Transparent,
                                        Color.White.copy(0.2f),
                                        Color.Transparent
                                    )
                                ),
                                width = 1.dp,
                                shape = RoundedCornerShape(8.dp)
                            )
                            .background(
                                color = Color(0x3378599A),
                                shape = RoundedCornerShape(8.dp)
                            )
                    ) {
                        // Keep talking设置（二状态，与全局设置同步）
                        agentInfo?.let { agent ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(56.dp)
                                    .padding(horizontal = 16.dp)
                                    .noRippleClickable {
                                        // 检查是否正式登录（非游客且已登录）
                                        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                            agentKeepTalking = !agentKeepTalking
                                            IntySetting.setAgentKeepTalking(
                                                agent.id,
                                                agentKeepTalking
                                            )
                                            // 更新按钮显示状态
                                            shouldShowButton = agentKeepTalking
                                        } else {
                                            // 未登录或游客时跳转到登录页面
                                            TheRouter.build(Constant.ROUTE_LOGIN)
                                                .navigation(context)
                                        }
                                    },
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = stringResource(R.string.settings_keep_talking),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Normal,
                                    color = Color.White
                                )
                                Spacer(Modifier.weight(1f))
                                Image(
                                    painter = if (agentKeepTalking) painterResource(R.drawable.opened) else painterResource(
                                        R.drawable.closed
                                    ),
                                    contentDescription = null,
                                )
                            }
                            /*
                                                        // Premium model设置（二状态，与全局设置同步）
                                                        Row(
                                                            modifier = Modifier
                                                                .fillMaxWidth()
                                                                .height(56.dp)
                                                                .padding(horizontal = 16.dp)
                                                                .noRippleClickable {
                                                                    // 检查是否正式登录（非游客且已登录）
                                                                    if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                                                        // 检查VIP状态
                                                                        if (!vipStatus.isSubscribed) {
                                                                            // 如果不是VIP，显示提示
                                                                            Toast.makeText(
                                                                                context,
                                                                                youAreNotVipText,
                                                                                Toast.LENGTH_SHORT
                                                                            ).show()
                                                                        } else {
                                                                            // 如果是VIP，允许切换
                                                                            agentPremiumModel = !agentPremiumModel
                                                                            IntySetting.setAgentPremiumModel(
                                                                                agent.id,
                                                                                agentPremiumModel
                                                                            )
                                                                        }
                                                                    } else {
                                                                        // 未登录或游客时跳转到登录页面
                                                                        TheRouter.build(Constant.ROUTE_LOGIN)
                                                                            .navigation(context)
                                                                    }
                                                                },
                                                            verticalAlignment = Alignment.CenterVertically
                                                        ) {
                                                            Text(
                                                                text = premiumModelText,
                                                                fontSize = 14.sp,
                                                                fontWeight = FontWeight.Normal,
                                                                color = Color.White
                                                            )
                                                            Spacer(Modifier.weight(1f))
                                                            Image(
                                                                painter = if (agentPremiumModel) painterResource(R.drawable.opened) else painterResource(
                                                                    R.drawable.closed
                                                                ),
                                                                contentDescription = null,
                                                            )
                                                        }*/

                            // 举报入口
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(56.dp)
                                    .padding(horizontal = 16.dp)
                                    .noRippleClickable {
                                        // 检查是否正式登录（非游客且已登录）
                                        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                            TheRouter.build(Constant.ROUTE_REPORT)
                                                .withString("targetID", agent.id)
                                                .withString("targetType", "AGENT")
                                                .navigation(context)
                                        } else {
                                            // 未登录或游客时跳转到登录页面
                                            TheRouter.build(Constant.ROUTE_LOGIN)
                                                .navigation(context)
                                        }
                                    },
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = stringResource(R.string.report),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Normal,
                                    color = Color.White
                                )
                                Spacer(Modifier.weight(1f))
                                Image(
                                    painter = painterResource(R.drawable.icon_next),
                                    contentDescription = null,
                                )
                            }

                        }


                        // 暂时隐藏 Auto-play语音消息设置
                        /*
                        Row(
                            modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp)
                                .noRippleClickable {
                                    // 检查是否正式登录（非游客且已登录）
                                    if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                        isAutoPlayAudio = !isAutoPlayAudio
                                        IntySetting.setAutoPlayAudio(isAutoPlayAudio)
                                    } else {
                                        // 未登录或游客时跳转到登录页面
                                        TheRouter.build(Constant.ROUTE_LOGIN)
                                            .navigation(context)
                                    }
                                },
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = stringResource(R.string.settings_auto_play_audio),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Normal,
                                color = Color.White

                            )
                            Spacer(Modifier.weight(1f))
                            Image(
                                painter = if (isAutoPlayAudio) painterResource(R.drawable.opened) else painterResource(R.drawable.closed),
                                contentDescription = null,
                            )
                        }
                        */
                    }

                }

            }
        ) {
            // 主屏内容
        }

    }
}

@Composable
private fun ChatItem(item: MsgInfo) {
    when (item.role) {
        "assistant" -> {
            ChatItemAI(item)
        }

        "user" -> {
            ChatItemUser(item)
        }

        else -> {
            EasyLog.log("unknown role: $item")
        }
    }
}

@Composable
private fun ChatItemAI(item: MsgInfo) {
    Row {
        Box(
            modifier = Modifier
                .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                .padding(12.dp, 13.dp)
                .widthIn(1.dp, 300.dp)
        ) {
            if (item.content == "loading_animation") {
                LoadingAnimation()
            } else {
                StyledMessageText(
                    text = item.content,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Normal,
                    normalColor = Color.White,
                    actionColor = Color.White.copy(0.55f)
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


@Composable
private fun ChatItemUser(item: MsgInfo) {
    Row {
        Spacer(
            modifier = Modifier
                .widthIn(80.dp)
                .weight(1f)
        )
        Box(
            modifier = Modifier
                .background(Color.White.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
                .padding(12.dp, 13.dp)
                .widthIn(1.dp, 300.dp)
        ) {
            StyledMessageText(
                text = item.content,
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
                normalColor = Color(0xff090909),
                actionColor = Color(0xff090909).copy(0.6f)
            )
        }
    }

}

@Composable
private fun StyledMessageText(
    text: String,
    fontSize: androidx.compose.ui.unit.TextUnit,
    fontWeight: FontWeight,
    normalColor: Color,
    actionColor: Color,
) {
    val annotatedText = buildAnnotatedString {
        var currentIndex = 0

        // Regex to match (text) and （text） patterns only
        val parenthesesRegex = Regex("\\(([^)]+)\\)")
        val chineseParenthesesRegex = Regex("（([^）]+)）")

        // Create a list of all matches (parentheses and chinese parentheses) with their types
        val allMatches = mutableListOf<Triple<IntRange, String, String>>() // range, content, type

        parenthesesRegex.findAll(text).forEach { match ->
            allMatches.add(Triple(match.range, match.groupValues[1], "parentheses"))
        }

        chineseParenthesesRegex.findAll(text).forEach { match ->
            allMatches.add(Triple(match.range, match.groupValues[1], "chinese_parentheses"))
        }

        // Sort matches by start position
        allMatches.sortBy { it.first.first }

        allMatches.forEach { (range, content, type) ->
            // Add text before the match
            if (range.first > currentIndex) {
                withStyle(
                    style = SpanStyle(
                        color = normalColor,
                        fontSize = fontSize,
                        fontWeight = fontWeight
                    )
                ) {
                    append(text.substring(currentIndex, range.first))
                }
            }

            // Add the styled text based on type
            withStyle(
                style = SpanStyle(
                    color = actionColor,
                    fontSize = fontSize,
                    fontWeight = fontWeight,
                    fontStyle = FontStyle.Italic
                )
            ) {
                when (type) {
                    "parentheses" -> {
                        // For parentheses, add the content with parentheses
                        append("($content)")
                    }

                    "chinese_parentheses" -> {
                        // For Chinese parentheses, add the content with Chinese parentheses
                        append("（$content）")
                    }
                }
            }

            currentIndex = range.last + 1
        }

        // Add remaining text after last match
        if (currentIndex < text.length) {
            withStyle(
                style = SpanStyle(
                    color = normalColor,
                    fontSize = fontSize,
                    fontWeight = fontWeight
                )
            ) {
                append(text.substring(currentIndex))
            }
        }
    }

    Text(
        text = annotatedText,
        fontSize = fontSize,
        fontWeight = fontWeight
    )
}


@Composable
private fun TopBar(
    modifier: Modifier,
    agentInfo: AgentInfo,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
    onClickMore: () -> Unit,
    onFollowAgent: ((String) -> Unit)? = null,
) {
    val context = LocalContext.current
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // 返回按钮
        if (showBackButton) {
            IntyImage(
                modifier = Modifier
                    .size(24.dp)
                    .noRippleClickable {
                        onBack?.invoke()
                    },
                model = R.drawable.back
            )
            Spacer(modifier = Modifier.width(8.dp))
        }

        Row(
            modifier = Modifier.background(
                color = Color(33, 0, 0, 77),
                shape = RoundedCornerShape(10.dp)
            ),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IntyCircleImage(
                modifier = Modifier
                    .padding(2.dp)
                    .size(36.dp)
                    .noRippleClickable {
                        TheRouter.build(Constant.ROUTE_AGENT_INFO)
                            .withObject("agent", agentInfo)
                            .navigation(context)
                    },
                url = agentInfo.avatar,
                placeholderResID = R.drawable.app_icon
            )

            Spacer(modifier = Modifier.width(6.dp))

            Text(
                text = agentInfo.name,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = Color.White
            )

            Spacer(modifier = Modifier.width(6.dp))

            if (!agentInfo.isFollowed) {
                IntyImage(
                    modifier = Modifier
                        .size(20.dp)
                        .noRippleClickable {
                            EasyLog.log("Follow button clicked - agentId: ${agentInfo.id}, current follow state: ${agentInfo.isFollowed}")
                            onFollowAgent?.invoke(agentInfo.id)
                        },
                    model = R.drawable.btn_add
                )
            }


            Spacer(modifier = Modifier.width(8.dp))
        }

        Spacer(modifier = Modifier.weight(1f))

        IntyImage(
            modifier = Modifier
                .size(20.dp)
                .noRippleClickable {
                    onClickMore()
                },
            model = R.drawable.icon_more
        )
    }

}


@Composable
private fun LoadingAnimation() {
    val infiniteTransition = rememberInfiniteTransition(label = "loading")

    Row(
        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        repeat(3) { index ->
            val delay = index * 200
            val dotAlpha by infiniteTransition.animateFloat(
                initialValue = 0.3f,
                targetValue = 1.0f,
                animationSpec = infiniteRepeatable(
                    animation = tween(600, delayMillis = delay)
                ), label = "dot_alpha_$index"
            )

            Box(
                modifier = Modifier
                    .size(6.dp)
                    .background(
                        color = Color.White.copy(dotAlpha * 0.7f),
                        shape = CircleShape
                    )
            )
        }
    }
}

@Composable
private fun MorePanelItem(
    icon: Int,
    text: String,
    onClick: () -> Unit,
) {

    Column(
        modifier = Modifier.noRippleClickable { onClick() },
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(Modifier.height(20.dp))
        Box(
            modifier = Modifier
                .size(64.dp)
                .background(color = Color.White.copy(0.05f), shape = RoundedCornerShape(8.dp))
        ) {
            Image(
                modifier = Modifier
                    .size(36.dp)
                    .align(Alignment.Center),
                painter = painterResource(id = icon),
                contentDescription = null
            )
        }
        Spacer(Modifier.height(6.dp))
        Text(
            text = text,
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
        )
        Spacer(Modifier.height(60.dp))
    }
}