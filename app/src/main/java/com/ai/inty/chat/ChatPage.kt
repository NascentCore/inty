package com.ai.inty.chat

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.runtime.derivedStateOf
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.IntySmallTextField
import com.ai.inty.base.MyModalNavigationDrawer
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.GENDER
import com.ai.inty.beans.MsgInfo
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.utils.getChatBackground
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import github.leavesczy.composebottomsheetdialog.BottomSheetDialog
import github.leavesczy.composebottomsheetdialog.DiaAmountLayout
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

@Composable
fun ChatPage(
    modifier: Modifier,
    chatViewModel: ChatViewModel,
    onFollowAgent: ((String) -> Unit)? = null,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,

) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val agentInfo = chatViewModel.agentInfo.collectAsState().value
    val focusManager = LocalFocusManager.current
    
    // 检测键盘状态
    val imeHeight = WindowInsets.ime.getBottom(density)
    val isKeyboardVisible = imeHeight > 0
    
    // 动态计算底部间距
    val bottomPadding = when {
        showBackButton -> 10.dp // 独立聊天页面：固定10dp
        isKeyboardVisible -> 10.dp // 首页聊天页面，键盘呼出时：10dp
        else -> 90.dp // 首页聊天页面，无键盘时：90dp（给底部tab留出更多间隔）
    }

    var isAutoPlayAudio by remember { mutableStateOf(IntySetting.isAutoPlayAudio()) }
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
            mutableStateOf(configuration.screenWidthDp)
        }
        var imageHeightDp by remember {
            mutableStateOf(configuration.screenHeightDp)
        }
        if (configuration.screenWidthDp > imageWidthDp) {
            imageWidthDp = configuration.screenWidthDp
        }
        if (configuration.screenHeightDp > imageHeightDp) {
            imageHeightDp = configuration.screenHeightDp
        }
        Column(
            modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState(), false)
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
        Box(modifier = Modifier
            .fillMaxWidth()
            .height(120.dp)
            .background(
                brush = Brush.verticalGradient(colors),
            )
        ) {
        }

        // 底部渐变遮罩 - 固定位置
        val bottomColors = listOf(
            Color(0x001C1523),
            Color(0xFF1C1523)
        )
        Box(modifier = Modifier
            .fillMaxWidth()
            .height(300.dp)
            .background(
                brush = Brush.verticalGradient(bottomColors),
            )
            .align(Alignment.BottomCenter)
        ) {
        }

        val drawerState = remember {
            mutableStateOf(DrawerValue.Closed)
        }
        val scope = rememberCoroutineScope()

        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0),
            topBar = {
            },

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

                LazyColumn(
                    modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                    reverseLayout = true,
                ) {
                    val msgs = chatViewModel.msgs
                    EasyLog.log("msgs count = ${msgs.size}")
                    item {
                        Spacer(
                            modifier = Modifier
                                .height(16.dp)
                                .fillMaxWidth()

                        )
                    }
                    itemsIndexed(msgs.filter { !(it.role == "user" && it.content == "continue") }) { index, item ->
                        ChatItem(item)
                        Spacer(
                            modifier = Modifier
                                .height(16.dp)
                                .fillMaxWidth()

                        )
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
                            .padding(start = 16.dp, top = 16.dp, end = 16.dp, bottom = bottomPadding)
                            .fillMaxWidth()
                            .background(Color(0x9937303D), RoundedCornerShape(24.dp))
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
                                modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
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

                            if (inputData.value.isNotEmpty()) {
                                IntyImage(
                                    modifier = Modifier.padding(16.dp, 0.dp).size(24.dp).noRippleClickable {
                                        chatViewModel.sendMsg()
                                    },
                                    model = R.drawable.btn_send
                                )
                            } else {
                                IntyImage(
                                    modifier = Modifier.padding(16.dp, 0.dp).size(24.dp).noRippleClickable {
                                        showMorePanel = !showMorePanel
                                    },
                                    model = if (showMorePanel) R.drawable.btn_down else R.drawable.btn_add2
                                )
                            }
                        }
                        
                        // 括号按钮区域 - 仅在输入框获得焦点时显示
                        if (isInputFocused.value) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 16.dp, vertical = 8.dp),
                                horizontalArrangement = androidx.compose.foundation.layout.Arrangement.Start
                            ) {
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
                                            val currentSelection = chatViewModel.inputSelection.value
                                            
                                            // 确保光标位置在有效范围内
                                            val safeSelection = currentSelection.coerceIn(0, currentText.length)
                                            
                                            // 在光标位置插入一对括号
                                            val beforeCursor = currentText.substring(0, safeSelection)
                                            val afterCursor = currentText.substring(safeSelection)
                                            val newText = beforeCursor + "()" + afterCursor
                                            
                                            // 更新文本
                                            chatViewModel.inputData.value = newText
                                            
                                            // 设置光标位置到括号中间
                                            val newCursorPosition = safeSelection + 1
                                            chatViewModel.inputSelection.value = newCursorPosition
                                        },
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = "( )",
                                        color = Color.White,
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Medium
                                    )
                                }
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

        MyModalNavigationDrawer(
            modifier = Modifier
            ,
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
                        text ="My Chat Persona",
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
                                    colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
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
                            value = when(userProfile.value.gender) {
                                GENDER.MALE.value -> "He/Him"
                                GENDER.FEMALE.value -> "She/Her"
                                else -> "They/Them"
                            },
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
                        text ="Chat Settings",
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
                                    colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
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
                                modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp)
                                    .noRippleClickable {
                                        // 检查是否正式登录（非游客且已登录）
                                        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                            agentKeepTalking = !agentKeepTalking
                                            IntySetting.setAgentKeepTalking(agent.id, agentKeepTalking)
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
                                    painter = if (agentKeepTalking) painterResource(R.drawable.opened) else painterResource(R.drawable.closed),
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
fun ChatItem(
    item: MsgInfo
) {
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
fun ChatItemAI(
    item: MsgInfo
) {
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
                    normalColor = Color.White.copy(0.55f),
                    actionColor = Color.White.copy(0.35f)
                )
            }
        }
        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
    }

}


@Composable
fun ChatItemUser(
    item: MsgInfo
) {
    Row {
        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
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
fun StyledMessageText(
    text: String,
    fontSize: androidx.compose.ui.unit.TextUnit,
    fontWeight: FontWeight,
    normalColor: Color,
    actionColor: Color
) {
    val annotatedText = buildAnnotatedString {
        var currentIndex = 0
        
        // Combined regex to match both *text* and (text) patterns
        val asteriskRegex = Regex("\\*([^*]+)\\*")
        val parenthesesRegex = Regex("\\(([^)]+)\\)")
        
        // Create a list of all matches (both asterisk and parentheses) with their types
        val allMatches = mutableListOf<Triple<IntRange, String, String>>() // range, content, type
        
        asteriskRegex.findAll(text).forEach { match ->
            allMatches.add(Triple(match.range, match.groupValues[1], "asterisk"))
        }
        
        parenthesesRegex.findAll(text).forEach { match ->
            allMatches.add(Triple(match.range, match.groupValues[1], "parentheses"))
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
                    "asterisk" -> {
                        // For asterisk, just add the content without the asterisks
                        append(content)
                    }
                    "parentheses" -> {
                        // For parentheses, add the content with parentheses
                        append("($content)")
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
fun TopBar(
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
            modifier = Modifier.background(color = Color(33, 0, 0, 77), shape = RoundedCornerShape(10.dp)),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IntyCircleImage(
                modifier = Modifier.padding(2.dp).size(36.dp)
                    .noRippleClickable {
                        TheRouter.build(Constant.ROUTE_AGENT_INFO)
                            .withObject("agent", agentInfo)
                            .navigation(context)
                    }
                ,
                url = agentInfo.avatar,
                placeholderResID = R.drawable.app_2
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
                    modifier = Modifier.size(20.dp).noRippleClickable {
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
            modifier = Modifier.size(20.dp).noRippleClickable {
                onClickMore()
            },
            model = R.drawable.icon_more
        )
    }

}


@Composable
fun LoadingAnimation() {
    val infiniteTransition = rememberInfiniteTransition(label = "loading")
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(800)
        ), label = "alpha"
    )
    
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
fun MorePanelItem(
    icon: Int,
    text: String,
    onClick: () -> Unit
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
                modifier = Modifier.size(36.dp).align(Alignment.Center),
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