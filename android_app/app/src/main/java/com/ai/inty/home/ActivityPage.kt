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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
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

enum class ActivityPageSubTab {
    TabMessage,
    TabFollowing
}

/**
 * 主页面第二个tab，会话列表页面，包含关注和聊天列表
 */
@Composable
fun ActivityPage(
    modifier: Modifier,
    selectedTab: ActivityPageSubTab,
    conversations: List<ConversationItem>,
    followingAgents: List<AgentInfo>,
    lastSysMsg: SysMsgItem?,
    onSelectTab: (ActivityPageSubTab) -> Unit,
    onClickConversationItem: (ConversationItem) -> Unit,
    onClickSysMsg: () -> Unit,
    onClickFollowingAgent: (AgentInfo) -> Unit,
    onUnfollowAgent: ((String) -> Unit)? = null,
    isLoadingConversations: Boolean = false,
    isLoadingFollowingAgents: Boolean = false,
    onLoadMoreConversations: (() -> Unit)? = null,
    onLoadMoreFollowingAgents: (() -> Unit)? = null,
) {
    Box(modifier = modifier) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )
        Content(
            selectedTab = selectedTab,
            conversations = conversations,
            followingAgents = followingAgents,
            lastSysMsg = lastSysMsg,
            onSelectTab = onSelectTab,
            onClickConversationItem = onClickConversationItem,
            onClickSysMsg = onClickSysMsg,
            onClickFollowingAgent = onClickFollowingAgent,
            onUnfollowAgent = onUnfollowAgent,
            isLoadingConversations = isLoadingConversations,
            isLoadingFollowingAgents = isLoadingFollowingAgents,
            onLoadMoreConversations = onLoadMoreConversations,
            onLoadMoreFollowingAgents = onLoadMoreFollowingAgents
        )
    }
}

val TAB_CONTENT_SPACER_HEIGHT = 22.dp

@Composable
private fun Content(
    selectedTab: ActivityPageSubTab,
    conversations: List<ConversationItem>,
    followingAgents: List<AgentInfo>,
    lastSysMsg: SysMsgItem?,
    onSelectTab: (ActivityPageSubTab) -> Unit,
    onClickConversationItem: (ConversationItem) -> Unit,
    onClickSysMsg: () -> Unit,
    onClickFollowingAgent: (AgentInfo) -> Unit,
    onUnfollowAgent: ((String) -> Unit)? = null,
    isLoadingConversations: Boolean = false,
    isLoadingFollowingAgents: Boolean = false,
    onLoadMoreConversations: (() -> Unit)? = null,
    onLoadMoreFollowingAgents: (() -> Unit)? = null,
) {
    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Transparent),
        containerColor = Color.Transparent
    ) { innerPadding ->
        Column(modifier = Modifier.fillMaxSize()) {
            Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

            SubTabSelector(
                selectedTab = selectedTab,
                onSelectTab = onSelectTab
            )

            Spacer(Modifier.height(TAB_CONTENT_SPACER_HEIGHT))

            when (selectedTab) {
                ActivityPageSubTab.TabMessage -> {
                    MessageTabContent(
                        conversations = conversations,
                        lastSysMsg = lastSysMsg,
                        onClickConversationItem = onClickConversationItem,
                        onClickSysMsg = onClickSysMsg,
                        isLoading = isLoadingConversations,
                        onLoadMore = onLoadMoreConversations
                    )
                }

                ActivityPageSubTab.TabFollowing -> {
                    FollowingTabContent(
                        followingAgents = followingAgents,
                        onClickAgent = onClickFollowingAgent,
                        onUnfollowAgent = onUnfollowAgent,
                        isLoading = isLoadingFollowingAgents,
                        onLoadMore = onLoadMoreFollowingAgents
                    )
                }
            }
        }
    }
}

@Composable
private fun SubTabSelector(
    selectedTab: ActivityPageSubTab,
    onSelectTab: (ActivityPageSubTab) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
    ) {
        ActivityPageSubTabItem(
            modifier = Modifier.noRippleClickable {
                onSelectTab(ActivityPageSubTab.TabMessage)
            },
            text = stringResource(R.string.tab_message),
            isSelected = selectedTab == ActivityPageSubTab.TabMessage
        )

        Spacer(Modifier.width(15.dp))

        ActivityPageSubTabItem(
            modifier = Modifier.noRippleClickable {
                onSelectTab(ActivityPageSubTab.TabFollowing)
            },
            text = stringResource(R.string.tab_following),
            isSelected = selectedTab == ActivityPageSubTab.TabFollowing
        )
    }
}

val TAB_ITEM_WIDTH = 120.dp
val TAB_ITEM_HEIGHT = 38.dp
val COLOR_ORANGE = Color(0xFFFF905D)
val COLOR_PURPLE = Color(0xFFC122FF)

@Composable
fun ActivityPageSubTabItem(
    modifier: Modifier,
    text: String,
    isSelected: Boolean,
) {
    Column(modifier = modifier.size(TAB_ITEM_WIDTH, TAB_ITEM_HEIGHT)) {
        if (isSelected) {
            val colorStops = arrayOf(
                0.0f to COLOR_ORANGE,
                1.0f to COLOR_PURPLE
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
    conversations: List<ConversationItem>,
    lastSysMsg: SysMsgItem?,
    onClickConversationItem: (ConversationItem) -> Unit,
    onClickSysMsg: () -> Unit,
    isLoading: Boolean = false,
    onLoadMore: (() -> Unit)? = null,
) {
    val listState = rememberLazyListState()

    // 检测滚动到底部
    val shouldLoadMore by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val totalItems = layoutInfo.totalItemsCount
            val lastVisibleItem = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0

            // 当滚动到倒数第3项时触发加载更多
            totalItems > 0 && lastVisibleItem >= totalItems - 3 && !isLoading
        }
    }

    // 监听滚动状态，触发加载更多
    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore) {
            onLoadMore?.invoke()
        }
    }

    Box(Modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.matchParentSize()
        ) {
            // 系统消息
            lastSysMsg?.let { sysMsg ->
                item {
                    AuthClickable(onClick = onClickSysMsg) { authModifier ->
                        ChatItem(
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
            if (conversations.isNotEmpty()) {
                runCatching {
                    itemsIndexed(
                        items = conversations,
                        key = { index, conversion -> "${conversion.agentId}_$index" }
                    ) { index, conversion ->
                        AuthClickable(onClick = { onClickConversationItem(conversion) }) { authModifier ->
                            ChatItem(
                                modifier = authModifier.fillMaxWidth(),
                                conversation = conversion
                            )
                        }
                    }
                }.onFailure { it.printStackTrace() }
            }

            // 加载更多指示器
            if (isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(80.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            color = Color.White,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                }
            }
        }

        if (lastSysMsg == null && conversations.isEmpty() && !isLoading) {
            EmptyContentUI()
        }
    }
}

@Composable
private fun EmptyContentUI() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {


        IntyImage(model = R.drawable.group2085655908)

        Spacer(Modifier.height(16.dp))

        Text(
            modifier = Modifier
                .padding(horizontal = 16.dp)
                .align(Alignment.CenterHorizontally),
            text = stringResource(R.string.no_agent),
            color = Color.White.copy(0.55f),
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
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
    isLoading: Boolean = false,
    onLoadMore: (() -> Unit)? = null,
) {
    val listState = rememberLazyListState()

    // 检测滚动到底部
    val shouldLoadMore by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val totalItems = layoutInfo.totalItemsCount
            val lastVisibleItem = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0

            // 当滚动到倒数第3项时触发加载更多
            totalItems > 0 && lastVisibleItem >= totalItems - 3 && !isLoading
        }
    }

    // 监听滚动状态，触发加载更多
    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore) {
            onLoadMore?.invoke()
        }
    }

    if (followingAgents.isNotEmpty()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize()
        ) {
            runCatching {
                itemsIndexed(
                    items = followingAgents,
                    key = { index, agent -> "${agent.id}_$index" }
                ) { index, agent ->
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
            }.onFailure { it.printStackTrace() }

            // 加载更多指示器
            if (isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(80.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            color = Color.White,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                }
            }
        }
    } else if (!isLoading) {
        EmptyContentUI()
    }
}

val CHAT_ITEM_HEIGHT = 88.dp
val CHARACTER_AVATAR_SIZE = 56.dp
val CHARACTER_NAME_HEIGHT = 22.dp
val CHARACTER_LAST_MESSAGE_HEIGHT = 22.dp
val CHARACTER_INITIAL_FOLLOW_DATE_FONT_SIZE = 12.sp
val CHARACTER_NEW_MESSAGE_DOT_HEIGHT = 22.dp
val CHARACTER_DELETED_TEXT_FONT_SIZE = 15.sp
val CHARACTER_NAME_TO_DELETED_TEXT_PADDING = 4.dp
val CHARACTER_DELETED_TEXT_TO_LAST_MESSAGE_PADDING = 4.dp
val CHARACTER_LAST_MESSAGE_TO_INITIAL_FOLLOW_DATE_PADDING = 4.dp
val CHARACTER_INITIAL_FOLLOW_DATE_TO_NEW_MESSAGE_DOT_PADDING = 4.dp
val CHARACTER_NEW_MESSAGE_DOT_TO_RIGHT_PADDING = 13.dp

@Composable
fun ChatItem(
    modifier: Modifier,
    conversation: ConversationItem,
    placeholderID: Int = R.drawable.app_icon,
) {
    Row(
        modifier = modifier.height(CHAT_ITEM_HEIGHT),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(Modifier.width(16.dp))

        // 头像
        IntyImage(
            modifier = Modifier.size(CHARACTER_AVATAR_SIZE),
            model = conversation.agentAvatar,
            placeholder = painterResource(placeholderID)
        )

        Spacer(Modifier.width(CHARACTER_NAME_TO_DELETED_TEXT_PADDING))

        // 内容区域
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    modifier = Modifier.height(CHARACTER_NAME_HEIGHT),
                    text = conversation.agentName,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (conversation.isDeleted) {
                    Spacer(Modifier.width(CHARACTER_DELETED_TEXT_TO_LAST_MESSAGE_PADDING))
                    Text(
                        text = "(deleted)",
                        fontSize = CHARACTER_DELETED_TEXT_FONT_SIZE,
                        color = Color(0x8CFFFFFF),
                    )
                }
            }

            Spacer(Modifier.height(CHARACTER_LAST_MESSAGE_TO_INITIAL_FOLLOW_DATE_PADDING))
            Text(
                modifier = Modifier.height(CHARACTER_LAST_MESSAGE_HEIGHT),
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
                fontSize = CHARACTER_INITIAL_FOLLOW_DATE_FONT_SIZE,
                color = Color.White.copy(0.55f),
            )
            Spacer(Modifier.height(CHARACTER_INITIAL_FOLLOW_DATE_TO_NEW_MESSAGE_DOT_PADDING))
            Box(
                modifier = Modifier.height(CHARACTER_NEW_MESSAGE_DOT_HEIGHT),
                contentAlignment = Alignment.Center,
            ) {
                if (conversation.isNew) {
                    RedDot()
                }
            }
        }
        Spacer(Modifier.width(CHARACTER_NEW_MESSAGE_DOT_TO_RIGHT_PADDING))
    }
}

val FOLLOWING_AGENT_ITEM_HEIGHT = 88.dp
val FOLLOWING_AGENT_AVATAR_SIZE = 56.dp
val FOLLOWING_AGENT_NAME_TO_LAST_MESSAGE_PADDING = 14.dp
val FOLLOWING_AGENT_NAME_HEIGHT = 22.dp
val FOLLOWING_AGENT_LAST_MESSAGE_HEIGHT = 22.dp
val FOLLOWING_AGENT_LAST_MESSAGE_TO_INITIAL_FOLLOW_DATE_PADDING = 4.dp
val FOLLOWING_AGENT_INITIAL_FOLLOW_DATE_FONT_SIZE = 12.sp
val FOLLOWING_AGENT_INITIAL_FOLLOW_DATE_TO_RIGHT_PADDING = 13.dp

/**
 * 关注代理项组件
 */
@Composable
fun FollowingAgentItem(
    modifier: Modifier,
    agent: AgentInfo,
) {
    Row(
        modifier = modifier.height(FOLLOWING_AGENT_ITEM_HEIGHT),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(Modifier.width(16.dp))

        // 头像
        IntyImage(
            modifier = Modifier.size(FOLLOWING_AGENT_AVATAR_SIZE),
            model = agent.avatar,
            placeholder = painterResource(R.drawable.app_icon)
        )

        Spacer(Modifier.width(FOLLOWING_AGENT_NAME_TO_LAST_MESSAGE_PADDING))

        // 内容区域
        Column(modifier = Modifier.weight(1f)) {
            Text(
                modifier = Modifier.height(FOLLOWING_AGENT_NAME_HEIGHT),
                text = agent.name,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(Modifier.height(FOLLOWING_AGENT_LAST_MESSAGE_TO_INITIAL_FOLLOW_DATE_PADDING))
            Text(
                modifier = Modifier.height(FOLLOWING_AGENT_LAST_MESSAGE_HEIGHT),
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
                fontSize = FOLLOWING_AGENT_INITIAL_FOLLOW_DATE_FONT_SIZE,
                color = Color.White.copy(0.55f),
            )
        }
        Spacer(Modifier.width(FOLLOWING_AGENT_INITIAL_FOLLOW_DATE_TO_RIGHT_PADDING))
    }
}

val LONG_PRESS_UNFOLLOW_ITEM_PADDING = 16.dp
val LONG_PRESS_UNFOLLOW_ITEM_PADDING_HORIZONTAL = 20.dp
val LONG_PRESS_UNFOLLOW_ITEM_PADDING_VERTICAL = 2.dp
val LONG_PRESS_UNFOLLOW_ITEM_TEXT_FONT_SIZE = 16.sp
val LONG_PRESS_UNFOLLOW_ITEM_SHAPE = 8.dp

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
                .padding(LONG_PRESS_UNFOLLOW_ITEM_PADDING),
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
                shape = RoundedCornerShape(LONG_PRESS_UNFOLLOW_ITEM_SHAPE)
            ) {
                Row(
                    modifier = Modifier
                        .padding(horizontal = LONG_PRESS_UNFOLLOW_ITEM_PADDING_HORIZONTAL, vertical = LONG_PRESS_UNFOLLOW_ITEM_PADDING_VERTICAL)
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
                    horizontalArrangement = Arrangement.spacedBy(LONG_PRESS_UNFOLLOW_ITEM_PADDING_HORIZONTAL)
                ) {
                    Text(
                        text = stringResource(R.string.unfollow),
                        color = Color.White,
                        style = MaterialTheme.typography.bodyMedium,
                        fontSize = LONG_PRESS_UNFOLLOW_ITEM_TEXT_FONT_SIZE
                    )
                }
            }
        }
    }
}
