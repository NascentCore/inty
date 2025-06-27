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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
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
import com.ai.inty.MySettingItem
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
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import github.leavesczy.composebottomsheetdialog.BottomSheetDialog
import github.leavesczy.composebottomsheetdialog.DiaAmountLayout
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import com.ai.inty.utils.AuthClickable

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

    var isAutoPlayAudio by remember { mutableStateOf(IntySetting.isAutoPlayAudio()) }
    var agentKeepTalking by remember(agentInfo?.id) { 
        mutableStateOf(
            agentInfo?.let { IntySetting.getAgentKeepTalking(it.id) }
        ) 
    }
    
    // 用于实时更新按钮显示状态
    var shouldShowButton by remember(agentInfo?.id) {
        mutableStateOf(
            agentInfo?.let { IntySetting.shouldShowKeepTalking(it.id) } ?: false
        )
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
                model = agentInfo?.avatar,
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
                    itemsIndexed(msgs) { index, item ->
                        ChatItem(item)
                        Spacer(
                            modifier = Modifier
                                .height(16.dp)
                                .fillMaxWidth()

                        )
                    }
                }
                

                // 输入框区域 - 受键盘影响会向上推
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
                                        Spacer(modifier = Modifier.width(1.dp))
                                        Text(
                                            text = "▶",
                                            color = Color.White,
                                            fontSize = 12.sp
                                        )
                                    }
                                }
                            }
                            Spacer(modifier = Modifier.height(8.dp))
                    }
                    
                    // 输入框
                    Row(
                        modifier = Modifier
                            .padding(horizontal = 16.dp, vertical = 8.dp)
                            .fillMaxWidth()
                            .height(64.dp)
                            .background(Color(0x9937303D), RoundedCornerShape(24.dp)),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                    val inputData = chatViewModel.inputData.collectAsState()
                    IntySmallTextField(
                        modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                        value = inputData.value,
                        singleLine = true,
                        onValueChange = {
                            chatViewModel.inputData.value = it
                        },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(
                            onSend = {
                                chatViewModel.sendMsg()
                            }
                        )
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
                                    TheRouter.build(Constant.ROUTE_REPORT)
                                        .withString("targetID", agentInfo?.id)
                                        .navigation(context)
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
                        text ="Following",
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
                        AuthClickable(
                            onClick = {
                                TheRouter.build(Constant.ROUTE_SETTING_MY)
                                    .withObject("userProfile", userProfile.value)
                                    .navigation(context)
                            }
                        ) { authModifier ->
                            MySettingItem(
                                key = "Name",
                                value = userProfile.value.nickname,
                                onClick = {},
                                modifier = authModifier
                            )
                        }
                        AuthClickable(
                            onClick = {
                                TheRouter.build(Constant.ROUTE_SETTING_MY)
                                    .withObject("userProfile", userProfile.value)
                                    .navigation(context)
                            }
                        ) { authModifier ->
                            MySettingItem(
                                key = "My Pronoun",
                                value = when(userProfile.value.gender) {
                                    GENDER.MALE.value -> "He/Him"
                                    GENDER.FEMALE.value -> "She/Her"
                                    else -> "They/Them"
                                },
                                onClick = {},
                                modifier = authModifier
                            )
                        }
                        AuthClickable(
                            onClick = {
                                TheRouter.build(Constant.ROUTE_SETTING_MY)
                                    .withObject("userProfile", userProfile.value)
                                    .navigation(context)
                            }
                        ) { authModifier ->
                            MySettingItem(
                                key = "My Persona",
                                value = "Edit",
                                onClick = {},
                                modifier = authModifier
                            )
                        }
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
                        AuthClickable(
                            onClick = {
                                isAutoPlayAudio = !isAutoPlayAudio
                                IntySetting.setAutoPlayAudio(isAutoPlayAudio)
                            }
                        ) { authModifier ->
                            Row(
                                modifier = authModifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
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
                        }
                        // 角色专用的keep talking设置（三状态）
                        agentInfo?.let { agent ->
                            AuthClickable(
                                onClick = {
                                    val newValue = when (agentKeepTalking) {
                                        null -> true    // 跟随全局 -> 开启
                                        true -> false   // 开启 -> 关闭
                                        false -> null   // 关闭 -> 跟随全局
                                    }
                                    agentKeepTalking = newValue
                                    IntySetting.setAgentKeepTalking(agent.id, newValue)
                                    // 更新按钮显示状态
                                    shouldShowButton = IntySetting.shouldShowKeepTalking(agent.id)
                                }
                            ) { authModifier ->
                                Row(
                                    modifier = authModifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(
                                            text = "Keep Talking for ${agent.name}",
                                            fontSize = 14.sp,
                                            fontWeight = FontWeight.Normal,
                                            color = Color.White
                                        )
                                        Text(
                                            text = when (agentKeepTalking) {
                                                true -> "On"
                                                false -> "Off"
                                                null -> "Follow global setting"
                                            },
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Normal,
                                            color = Color.White.copy(0.6f)
                                        )
                                    }
                                    Spacer(Modifier.weight(1f))
                                    // 三状态图标显示
                                    when (agentKeepTalking) {
                                        true -> Image(
                                            painter = painterResource(R.drawable.opened),
                                            contentDescription = null,
                                        )
                                        false -> Image(
                                            painter = painterResource(R.drawable.closed),
                                            contentDescription = null,
                                        )
                                        null -> Text(
                                            text = "Auto",
                                            fontSize = 12.sp,
                                            color = Color.White.copy(0.7f)
                                        )
                                    }
                                }
                            }
                        }
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
            StyledMessageText(
                text = item.content,
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
                normalColor = Color.White.copy(0.55f),
                actionColor = Color.White.copy(0.35f)
            )
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
        val regex = Regex("\\*([^*]+)\\*")
        
        regex.findAll(text).forEach { matchResult ->
            // Add text before the match
            if (matchResult.range.first > currentIndex) {
                withStyle(
                    style = SpanStyle(
                        color = normalColor,
                        fontSize = fontSize,
                        fontWeight = fontWeight
                    )
                ) {
                    append(text.substring(currentIndex, matchResult.range.first))
                }
            }
            
            // Add the action/thought text (content between asterisks)
            withStyle(
                style = SpanStyle(
                    color = actionColor,
                    fontSize = fontSize,
                    fontWeight = fontWeight,
                    fontStyle = FontStyle.Italic
                )
            ) {
                append(matchResult.groupValues[1])
            }
            
            currentIndex = matchResult.range.last + 1
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

            IntyImage(
                modifier = Modifier.size(20.dp).noRippleClickable {
                    EasyLog.log("Follow button clicked - agentId: ${agentInfo.id}, current follow state: ${agentInfo.isFollowed}")
                    onFollowAgent?.invoke(agentInfo.id)
                },
                model = if (agentInfo.isFollowed) R.drawable.checked else R.drawable.btn_add
            )


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