package com.ai.inty.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.DpOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.RedDot
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.ConversationItem
import com.ai.inty.beans.SysMsgItem
import com.ai.inty.utils.AuthClickable

import com.inty.utils.formatTimestampToDateTime

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

enum class ConversionsPageTab {
    TabMessage,
    TabFollowing
}

/**
 * 主页面第二个tab，会话列表页面，包含关注和聊天列表
 */
@Composable
fun ConversionsPage(
    modifier: Modifier,
    selectedTab: ConversionsPageTab,
    conversions: List<ConversationItem>,
    followingAgents: List<AgentInfo>,
    lastSysMsg: SysMsgItem?,
    onSelectTab: (ConversionsPageTab) -> Unit,
    onClickConversionItem: (ConversationItem) -> Unit,
    onClickSysMsg: () -> Unit,
    onClickFollowingAgent: (AgentInfo) -> Unit,
    onUnfollowAgent: ((String) -> Unit)? = null,
) {
    Box(modifier = modifier) {
        // 背景图片
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )

        // 主内容
        ConversionsPageContent(
            selectedTab = selectedTab,
            conversions = conversions,
            followingAgents = followingAgents,
            lastSysMsg = lastSysMsg,
            onSelectTab = onSelectTab,
            onClickConversionItem = onClickConversionItem,
            onClickSysMsg = onClickSysMsg,
            onClickFollowingAgent = onClickFollowingAgent,
            onUnfollowAgent = onUnfollowAgent
        )
    }
}

/**
 * 会话页面主内容
 */
@Composable
private fun ConversionsPageContent(
    selectedTab: ConversionsPageTab,
    conversions: List<ConversationItem>,
    followingAgents: List<AgentInfo>,
    lastSysMsg: SysMsgItem?,
    onSelectTab: (ConversionsPageTab) -> Unit,
    onClickConversionItem: (ConversationItem) -> Unit,
    onClickSysMsg: () -> Unit,
    onClickFollowingAgent: (AgentInfo) -> Unit,
    onUnfollowAgent: ((String) -> Unit)? = null,
) {
    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Transparent),
        containerColor = Color.Transparent
    ) { innerPadding ->
        Column {
            Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

            // Tab选择器
            ConversionsTabSelector(
                selectedTab = selectedTab,
                onSelectTab = onSelectTab
            )

            Spacer(Modifier.height(22.dp))

            // 内容区域
            when (selectedTab) {
                ConversionsPageTab.TabMessage -> {
                    MessageTabContent(
                        conversions = conversions,
                        lastSysMsg = lastSysMsg,
                        onClickConversionItem = onClickConversionItem,
                        onClickSysMsg = onClickSysMsg
                    )
                }

                ConversionsPageTab.TabFollowing -> {
                    FollowingTabContent(
                        followingAgents = followingAgents,
                        onClickAgent = onClickFollowingAgent,
                        onUnfollowAgent = onUnfollowAgent
                    )
                }
            }
        }
    }
}

/**
 * Tab选择器组件
 */
@Composable
private fun ConversionsTabSelector(
    selectedTab: ConversionsPageTab,
    onSelectTab: (ConversionsPageTab) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
    ) {
        ConversionsPageTabItem(
            modifier = Modifier.noRippleClickable {
                onSelectTab(ConversionsPageTab.TabMessage)
            },
            text = stringResource(R.string.tab_message),
            isSelected = selectedTab == ConversionsPageTab.TabMessage
        )

        Spacer(Modifier.width(15.dp))

        ConversionsPageTabItem(
            modifier = Modifier.noRippleClickable {
                onSelectTab(ConversionsPageTab.TabFollowing)
            },
            text = stringResource(R.string.tab_following),
            isSelected = selectedTab == ConversionsPageTab.TabFollowing
        )
    }
}

/**
 * Tab项组件
 */
@Composable
fun ConversionsPageTabItem(
    modifier: Modifier,
    text: String,
    isSelected: Boolean,
) {
    Column(modifier = modifier.size(120.dp, 38.dp)) {
        if (isSelected) {
            val colorStops = arrayOf(
                0.0f to Color(0xFFFF905D),
                1.0f to Color(0xFFC122FF)
            )
            val brush = Brush.horizontalGradient(colorStops = colorStops)

            Text(
                modifier = Modifier.align(Alignment.CenterHorizontally),
                text = text,
                style = TextStyle(
                    brush = brush,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                ),
            )
            IntyImage(
                modifier = Modifier.fillMaxWidth(),
                model = R.drawable.group43027
            )
        } else {
            Text(
                modifier = Modifier.align(Alignment.CenterHorizontally),
                text = text,
                style = TextStyle(
                    color = Color.White,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            )
        }
    }
}

/**
 * 消息Tab内容
 */
@Composable
private fun MessageTabContent(
    conversions: List<ConversationItem>,
    lastSysMsg: SysMsgItem?,
    onClickConversionItem: (ConversationItem) -> Unit,
    onClickSysMsg: () -> Unit,
) {
    LazyColumn {
        // 系统消息
        lastSysMsg?.let { sysMsg ->
            item {
                AuthClickable(onClick = onClickSysMsg) { authModifier ->
                    ConversationItem(
                        modifier = authModifier
                            .fillMaxWidth()
                            .background(color = Color(0x3378599A)),
                        conversation = ConversationItem(
                            agentId = Constant.SYS_NOTIFICATION_ID,
                            agentName = "System Notification",
                            lastMessage = sysMsg.content,
                            createdAt = sysMsg.createdAt
                        ),
                        placeholderID = R.drawable.icon_sys_notify
                    )
                }
            }
        }

        // 会话列表
        items(
            items = conversions,
            key = { conversion -> conversion.agentId }
        ) { conversion ->
            AuthClickable(onClick = { onClickConversionItem(conversion) }) { authModifier ->
                ConversationItem(
                    modifier = authModifier.fillMaxWidth(),
                    conversation = conversion
                )
            }
        }
    }
}

/**
 * 关注Tab内容
 */
@Composable
private fun FollowingTabContent(
    followingAgents: List<AgentInfo>,
    onClickAgent: (AgentInfo) -> Unit,
    onUnfollowAgent: ((String) -> Unit)? = null,
) {
    LazyColumn {

        items(
            items = followingAgents,
            key = { agent -> agent.id }
        ) { agent ->
            if (onUnfollowAgent != null) {
                LongPressUnfollowItem(
                    agent = agent,
                    onClickAgent = onClickAgent,
                    onUnfollowAgent = onUnfollowAgent
                )
            } else {
                FollowingAgentItem(
                    modifier = Modifier
                        .fillMaxWidth()
                        .noRippleClickable { onClickAgent(agent) },
                    agent = agent
                )
            }
        }
    }
}

/**
 * 会话项组件
 */
@Composable
fun ConversationItem(
    modifier: Modifier,
    conversation: ConversationItem,
    placeholderID: Int = R.drawable.app_icon,
) {
    Row(
        modifier = modifier.height(88.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(Modifier.width(16.dp))

        // 头像
        IntyImage(
            modifier = Modifier.size(56.dp),
            model = conversation.agentAvatar,
            placeholder = painterResource(placeholderID)
        )

        Spacer(Modifier.width(14.dp))

        // 内容区域
        Column(modifier = Modifier.weight(1f)) {
            Text(
                modifier = Modifier.height(22.dp),
                text = conversation.agentName,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(Modifier.height(4.dp))
            Text(
                modifier = Modifier.height(22.dp),
                text = conversation.lastMessage,
                fontSize = 14.sp,
                color = Color.White.copy(0.55f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }

        // 右侧信息
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = conversation.getShowTime(),
                fontSize = 12.sp,
                color = Color.White.copy(0.55f),
            )
            Spacer(Modifier.height(4.dp))
            Box(
                modifier = Modifier.height(22.dp),
                contentAlignment = Alignment.Center,
            ) {
                if (conversation.isNew) {
                    RedDot()
                }
            }
        }
        Spacer(Modifier.width(13.dp))
    }
}

/**
 * 关注代理项组件
 */
@Composable
fun FollowingAgentItem(
    modifier: Modifier,
    agent: AgentInfo,
) {
    Row(
        modifier = modifier.height(88.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(Modifier.width(16.dp))

        // 头像
        IntyImage(
            modifier = Modifier.size(56.dp),
            model = agent.avatar,
            placeholder = painterResource(R.drawable.app_icon)
        )

        Spacer(Modifier.width(14.dp))

        // 内容区域
        Column(modifier = Modifier.weight(1f)) {
            Text(
                modifier = Modifier.height(22.dp),
                text = agent.name,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(Modifier.height(4.dp))
            Text(
                modifier = Modifier.height(22.dp),
                text = agent.opening,
                fontSize = 14.sp,
                color = Color.White.copy(0.55f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }

        // 右侧信息
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = formatTimestampToDateTime(agent.createdAt),
                fontSize = 12.sp,
                color = Color.White.copy(0.55f),
            )
        }
        Spacer(Modifier.width(13.dp))
    }
}

/**
 * 长按取消关注项组件
 */
@Composable
fun LongPressUnfollowItem(
    agent: AgentInfo,
    onClickAgent: (AgentInfo) -> Unit,
    onUnfollowAgent: (String) -> Unit,
) {
    var isDeleting by remember { mutableStateOf(false) }
    var showPopup by remember { mutableStateOf(false) }
    var longPressOffset by remember { mutableStateOf(DpOffset.Zero) }

    // 如果正在删除，显示加载状态
    if (isDeleting) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF1C1523))
                .padding(16.dp),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator(
                color = Color.White,
                modifier = Modifier.size(24.dp)
            )
        }
    } else {
        Box {
            FollowingAgentItem(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF1C1523))
                    .pointerInput(Unit) {
                        val height = size.height.toDp()
                        detectTapGestures(
                            onTap = {
                                onClickAgent(agent)
                            },
                            onLongPress = { offset ->
                                // 获取长按位置并转换为Dp
                                val xDp = offset.x.toDp()
                                val yDp = offset.y.toDp()
                                longPressOffset = DpOffset(x = xDp, y = yDp - height)
                                showPopup = true
                            }
                        )
                    },
                agent = agent
            )

            // 长按弹出菜单
            DropdownMenu(
                expanded = showPopup,
                onDismissRequest = { showPopup = false },
                offset = longPressOffset,
                containerColor = Color(0xFF2A1F2E),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier
                        .padding(horizontal = 20.dp, vertical = 2.dp)
                        .clickable(onClick = {
                            showPopup = false
                            isDeleting = true
                            onUnfollowAgent(agent.id)
                            // 延迟重置删除状态
                            CoroutineScope(Dispatchers.Main).launch {
                                delay(500)
                                isDeleting = false
                            }
                        }),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = stringResource(R.string.unfollow),
                        color = Color.White,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
    }
}
