package com.ai.intellimate.messages

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.design.theme.brushes
import ai.sxwl.android.design.theme.textOnLightSurface
import ai.sxwl.android.design.ui.HeartRedDot
import ai.sxwl.android.utils.TimeUtils
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInParent
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.EmptyDataState

/** 主页面第二个tab，会话列表页面，包含关注和聊天列表 */
@Composable
fun MessagesPage(
    modifier: Modifier = Modifier,
    viewModel: MessagesViewModel,
    onClickConversationItem: (ConversationItem) -> Unit,
    onClickFavoriteAgent: (AgentInfo) -> Unit = {},
    onNavigateToExplore: () -> Unit = {},
    onOpenSubscription: () -> Unit = {},
    pageTrackingContext: String = "MessagesPage",
) {
    val uiState by viewModel.uiState.collectAsState()

    // 页面跟踪（首次加载时）
    LaunchedEffect(pageTrackingContext) { viewModel.trackPageView(pageTrackingContext) }

    // 监听会话列表更新，检查是否有新消息自动取消隐藏
    LaunchedEffect(uiState.conversations) { viewModel.checkAndUnhideConversations() }

    // 当页面显示时，主动刷新 IntelliMate agent（如果缓存中没有）
    LaunchedEffect(Unit) { viewModel.refreshIntelliMateAgentIfNeeded() }

    // 收藏列表仅在页面进入时拉取一次，返回该页时会重新触发
    LaunchedEffect(Unit) { viewModel.loadFavoriteAgents() }

    Box(modifier = modifier) {
        AsyncImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg,
            contentDescription = null,
        )
        Content(
            uiState = uiState,
            viewModel = viewModel,
            onClickConversationItem = onClickConversationItem,
            onLoadMore = { viewModel.loadMoreConversations() },
            onClickFavoriteAgent = onClickFavoriteAgent,
            onNavigateToExplore = onNavigateToExplore,
            onOpenSubscription = onOpenSubscription,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Content(
    uiState: MessagesUiState,
    viewModel: MessagesViewModel,
    onClickConversationItem: (ConversationItem) -> Unit,
    onLoadMore: () -> Unit,
    onClickFavoriteAgent: (AgentInfo) -> Unit,
    onNavigateToExplore: () -> Unit,
    onOpenSubscription: () -> Unit,
) {
    Scaffold(
        modifier = Modifier.fillMaxSize().background(Color.Transparent),
        containerColor = Color.Transparent,
        topBar = {
            TopAppBar(
                title = {
                    Image(
                        painter = painterResource(R.drawable.img_message_title),
                        contentDescription = null,
                        modifier = Modifier.height(30.dp).fillMaxWidth(),
                        contentScale = ContentScale.Fit,
                        alignment = Alignment.CenterStart,
                    )
                },
                modifier = Modifier,
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )
        },
    ) { innerPadding ->
        Column(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            MessageTabContent(
                uiState = uiState,
                viewModel = viewModel,
                onClickConversationItem = onClickConversationItem,
                onLoadMore = onLoadMore,
                onClickFavoriteAgent = onClickFavoriteAgent,
                onNavigateToExplore = onNavigateToExplore,
                onOpenSubscription = onOpenSubscription,
            )
        }
    }
}

/** 消息Tab内容 */
@Composable
private fun MessageTabContent(
    uiState: MessagesUiState,
    viewModel: MessagesViewModel,
    onClickConversationItem: (ConversationItem) -> Unit,
    onLoadMore: () -> Unit,
    onClickFavoriteAgent: (AgentInfo) -> Unit,
    onNavigateToExplore: () -> Unit,
    onOpenSubscription: () -> Unit,
) {
    val selectedTab by viewModel.selectedTab.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        MessagesSubscriptionBanner(
            modifier =
                Modifier.fillMaxWidth().padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
            titleText = stringResource(R.string.messages_premium_banner_title),
            ctaText = stringResource(R.string.messages_premium_banner_cta),
            onClick = onOpenSubscription,
        )
        Spacer(Modifier.height(UiConfigs.Spacing.Medium))
        MessagesTabSwitcher(
            selectedTab = selectedTab,
            onTabSelected = { viewModel.setSelectedTab(it) },
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        )
        Spacer(Modifier.height(12.dp))
        when (selectedTab) {
            MessageSecondaryTab.Conversations -> {
                ConversationList(
                    uiState = uiState,
                    viewModel = viewModel,
                    conversations = uiState.conversations,
                    onClickConversationItem = onClickConversationItem,
                    onLoadMore = onLoadMore,
                )
            }
            MessageSecondaryTab.Intimate -> {
                // TODO: 该“亲密度排名”完全依赖本地 Room 数据库（本地聊天消息条数统计）进行排序；若本地 Room
                // 数据不完整（如清理缓存/换机/未全量同步等），这里展示的排名与数量将不准确。
                val counts = uiState.intimateMessageCounts
                val intimateConversations =
                    remember(uiState.conversations, counts, uiState.refreshKey) {
                        uiState.conversations.sortedWith(
                            compareByDescending<ConversationItem> { counts[it.agentId] ?: 0 }
                                .thenByDescending { conversation ->
                                    TimeUtils.parseIsoTimeToTimestamp(conversation.lastMessageTime)
                                        ?: 0L
                                }
                        )
                    }
                ConversationList(
                    uiState = uiState,
                    viewModel = viewModel,
                    conversations = intimateConversations,
                    onClickConversationItem = onClickConversationItem,
                    onLoadMore = onLoadMore,
                    messageCounts = counts,
                    showMessageCount = true,
                )
            }
            MessageSecondaryTab.Favorites -> {
                FavoriteAgentsContent(
                    favoriteAgents = uiState.favoriteAgents,
                    isLoading = uiState.isLoadingFavorites,
                    onClickAgent = onClickFavoriteAgent,
                    onNavigateToExplore = onNavigateToExplore,
                )
            }
        }
    }
}

/**
 * 消息页顶部订阅引导横幅：用于 Messages tab 顶部展示，提示升级订阅。
 *
 * 预期视觉效果：紫色横向渐变卡片，左侧两行文案，右侧明亮 CTA 按钮并带奖杯图标。
 *
 * 可配置项：modifier 控制外部布局；titleText/ctaText 控制文案；onClick 处理点击跳转。
 */
@Composable
private fun MessagesSubscriptionBanner(
    modifier: Modifier = Modifier,
    titleText: String,
    ctaText: String,
    onClick: () -> Unit,
) {
    Box(
        modifier =
            modifier
                .clip(RoundedCornerShape(UiConfigs.MessagesPage.PremiumBanner.CornerRadius))
                .drawBehind {
                    drawRect(
                        brush =
                            Brush.horizontalGradient(listOf(Color(0xFFC3D5FB), Color(0xFFC567F5)))
                    )
                }
                .clickable(onClick = onClick)
                .padding(vertical = 12.dp)
    ) {
        Column(
            modifier = Modifier.align(Alignment.Center).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = titleText,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.textOnLightSurface,
                overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 12.dp),
            )

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Row(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(horizontal = 16.dp)
                        .clip(
                            RoundedCornerShape(UiConfigs.MessagesPage.PremiumBanner.CtaCornerRadius)
                        )
                        .background(brush = MaterialTheme.brushes.gradientBrush4)
                        .padding(
                            horizontal = UiConfigs.MessagesPage.PremiumBanner.CtaHorizontalPadding,
                            vertical = UiConfigs.MessagesPage.PremiumBanner.CtaVerticalPadding,
                        ),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
            ) {
                Icon(
                    painter = painterResource(R.drawable.icon_messages_subscription),
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.textOnLightSurface,
                    modifier = Modifier.size(14.dp, 10.dp),
                )
                Spacer(Modifier.width(UiConfigs.MessagesPage.PremiumBanner.CtaIconTextSpacing))
                Text(
                    text = ctaText,
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.textOnLightSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Preview
@Composable
private fun MessagesSubscriptionBannerPreview() {
    IntelliMateTheme() {
        MessagesSubscriptionBanner(
            modifier =
                Modifier.fillMaxWidth().padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
            titleText = stringResource(R.string.messages_premium_banner_title),
            ctaText = stringResource(R.string.messages_premium_banner_cta),
            onClick = {},
        )
    }
}

internal enum class MessageSecondaryTab {
    Conversations,
    Intimate,
    Favorites,
}

@Composable
private fun ConversationList(
    uiState: MessagesUiState,
    viewModel: MessagesViewModel,
    conversations: List<ConversationItem>,
    onClickConversationItem: (ConversationItem) -> Unit,
    onLoadMore: () -> Unit,
    messageCounts: Map<String, Int> = emptyMap(),
    showMessageCount: Boolean = false,
) {
    val listState = rememberLazyListState()
    val shouldLoadMore by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val totalItems = layoutInfo.totalItemsCount
            val lastVisibleItem = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0

            totalItems > 0 &&
                lastVisibleItem >= totalItems - 3 &&
                !uiState.isLoading &&
                uiState.hasMore
        }
    }

    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore) {
            onLoadMore()
        }
    }

    var showMenuForConversationId by remember { mutableStateOf<String?>(null) }
    val itemPositions = remember { mutableStateMapOf<String, Float>() }
    var lazyColumnY by remember { mutableStateOf(0f) }
    val density = LocalDensity.current

    Box(Modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            modifier =
                Modifier.matchParentSize().onGloballyPositioned { coordinates ->
                    lazyColumnY = with(density) { coordinates.positionInParent().y.toDp().value }
                },
        ) {
            if (uiState.isRefreshing) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth().height(80.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        CircularProgressIndicator(
                            color = Color.White,
                            modifier = Modifier.size(24.dp),
                        )
                    }
                }
            }

            if (conversations.isNotEmpty()) {
                runCatching {
                        itemsIndexed(
                            items = conversations,
                            key = { index, conversion ->
                                "${conversion.agentId}_${conversion.isPinned}_${uiState.refreshKey}_${index}"
                            },
                        ) { index, conversion ->
                            var lastClickTime by remember { mutableStateOf(0L) }

                            val isIntelliMate = conversion.agentId in uiState.intelliMateAgentIds
                            val isPinned =
                                remember(conversion.agentId, uiState.refreshKey) {
                                    conversion.isPinned
                                }
                            val showPushIndicator = conversion.agentId in uiState.pushAgentIds

                            val density = LocalDensity.current
                            Box(
                                modifier =
                                    Modifier.fillMaxWidth()
                                        .onGloballyPositioned { coordinates ->
                                            val itemYInLazyColumn =
                                                with(density) {
                                                    coordinates.positionInParent().y.toDp().value
                                                }
                                            itemPositions[conversion.agentId] =
                                                itemYInLazyColumn + lazyColumnY
                                        }
                                        .combinedClickable(
                                            onClick = {
                                                if (showMenuForConversationId != null) {
                                                    showMenuForConversationId = null
                                                    return@combinedClickable
                                                }

                                                val currentTime = System.currentTimeMillis()
                                                if (AntiClick.isValidClick(lastClickTime)) {
                                                    lastClickTime = currentTime
                                                    if (
                                                        IntySetting.isLogin() &&
                                                            IntySetting.getCurToken().isNotEmpty()
                                                    ) {
                                                        viewModel.clearConversationPush(
                                                            conversion.agentId
                                                        )
                                                        onClickConversationItem(conversion)
                                                    }
                                                }
                                            },
                                            onLongClick = {
                                                showMenuForConversationId =
                                                    if (
                                                        showMenuForConversationId ==
                                                            conversion.agentId
                                                    ) {
                                                        null
                                                    } else {
                                                        conversion.agentId
                                                    }
                                            },
                                        )
                            ) {
                                ChatHistoryItem(
                                    modifier = Modifier.fillMaxWidth(),
                                    conversation = conversion,
                                    showPushIndicator = showPushIndicator,
                                    messageCount =
                                        if (showMessageCount) messageCounts[conversion.agentId]
                                        else null,
                                )
                            }
                        }
                        item { Spacer(Modifier.height(60.dp)) }
                    }
                    .onFailure { it.printStackTrace() }
            }
        }

        if (showMenuForConversationId != null) {
            val conversation = conversations.find { it.agentId == showMenuForConversationId }
            conversation?.let { conv ->
                val isIntelliMate = conv.agentId in uiState.intelliMateAgentIds
                val menuY = itemPositions[conv.agentId]?.let { it.dp } ?: 0.dp
                ConversationItemMenu(
                    isPinned = conv.isPinned,
                    isHidden = conv.isHidden,
                    onPinClick = {
                        if (conv.isPinned) {
                            viewModel.unpinConversation(conv.agentId)
                        } else {
                            viewModel.pinConversation(conv.agentId)
                        }
                        showMenuForConversationId = null
                    },
                    onHideClick = {
                        if (conv.isHidden) {
                            viewModel.unhideConversation(conv.agentId)
                        } else {
                            viewModel.hideConversation(conv.agentId)
                        }
                        showMenuForConversationId = null
                    },
                    onDismiss = { showMenuForConversationId = null },
                    showHideOption = !isIntelliMate,
                    modifier = Modifier.offset(x = 16.dp, y = menuY).width(140.dp).zIndex(1000f),
                )
            }
        }

        if (conversations.isEmpty() && !uiState.isLoading && !uiState.isRefreshing) {
            EmptyDataState(
                subtitle = stringResource(R.string.empty_conversations),
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

@Composable
private fun MessagesTabSwitcher(
    selectedTab: MessageSecondaryTab,
    onTabSelected: (MessageSecondaryTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tabs =
        listOf(
            MessageSecondaryTab.Conversations to
                stringResource(R.string.messages_tab_conversations),
            MessageSecondaryTab.Intimate to stringResource(R.string.messages_tab_intimate),
            MessageSecondaryTab.Favorites to stringResource(R.string.messages_tab_favorites),
        )
    val selectedIndex = tabs.indexOfFirst { it.first == selectedTab }.coerceAtLeast(0)

    TabRow(
        selectedTabIndex = selectedIndex,
        containerColor = Color.Transparent,
        contentColor = Color.White,
        indicator = { tabPositions ->
            if (tabPositions.isNotEmpty()) {
                TabRowDefaults.Indicator(
                    modifier =
                        Modifier.tabIndicatorOffset(tabPositions[selectedIndex]).height(2.dp),
                    color = Color.White,
                )
            }
        },
        divider = {},
        modifier = modifier,
    ) {
        tabs.forEach { (tab, title) ->
            val selected = tab == selectedTab
            Tab(
                selected = selected,
                onClick = { onTabSelected(tab) },
                text = {
                    Text(
                        text = title,
                        color = if (selected) Color.White else Color.White.copy(alpha = 0.6f),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                },
            )
        }
    }
}

@Composable
private fun FavoriteAgentsContent(
    favoriteAgents: List<AgentInfo>,
    isLoading: Boolean,
    onClickAgent: (AgentInfo) -> Unit,
    onNavigateToExplore: () -> Unit,
) {
    when {
        isLoading -> {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color.White, modifier = Modifier.size(32.dp))
            }
        }
        favoriteAgents.isEmpty() -> {
            EmptyDataState(
                title = stringResource(R.string.messages_favorites_empty_title),
                subtitle = stringResource(R.string.messages_favorites_empty_subtitle),
                showRetryButton = true,
                actionTextResId = R.string.messages_favorites_empty_explore_cta,
                onRetry = onNavigateToExplore,
                modifier = Modifier.fillMaxSize(),
            )
        }
        else -> {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                items(favoriteAgents, key = { it.id }) { agent ->
                    FavoriteAgentItem(agent = agent, onClick = onClickAgent)
                }
                item { Spacer(Modifier.height(60.dp)) }
            }
        }
    }
}

@Composable
private fun FavoriteAgentItem(agent: AgentInfo, onClick: (AgentInfo) -> Unit) {
    val avatarRes = getCdnImageUrl(agent.avatar, width = 128) ?: R.drawable.img_default_avatar
    Row(
        modifier =
            Modifier.fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 6.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(Color.White.copy(alpha = 0.06f))
                .clickable { onClick(agent) }
                .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AsyncImage(
            modifier = Modifier.size(56.dp).clip(CircleShape),
            model = avatarRes,
            placeholder = painterResource(R.drawable.img_default_avatar),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            alignment = Alignment.TopCenter,
        )
        Spacer(Modifier.width(14.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = agent.name,
                fontSize = 15.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            val subtitle =
                when {
                    agent.intro.isNotBlank() -> agent.intro
                    agent.opening.isNotBlank() -> agent.opening
                    else -> null
                }
            subtitle?.let {
                Spacer(Modifier.height(4.dp))
                Text(
                    text = it,
                    fontSize = 13.sp,
                    lineHeight = 20.sp,
                    color = Color(0x99FFFFFF),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        Icon(
            imageVector = Icons.Filled.Favorite,
            contentDescription = null,
            tint = Color(0xFFFF5A8A),
            modifier = Modifier.size(20.dp),
        )
    }
}

@Composable
private fun ChatHistoryItem(
    modifier: Modifier,
    conversation: ConversationItem,
    placeholderID: Int = R.drawable.img_default_avatar,
    showPushIndicator: Boolean = false,
    messageCount: Int? = null,
) {
    // 每次重组时重新读取 isPinned 值，确保获取最新状态
    val isPinned = conversation.isPinned
    Row(modifier = modifier.height(88.dp), verticalAlignment = Alignment.CenterVertically) {
        Spacer(Modifier.width(16.dp))

        // 头像
        val avatarRes =
            getCdnImageUrl(conversation.agentAvatar, width = 128) ?: R.drawable.img_default_avatar
        Box(modifier = Modifier.size(56.dp)) {
            AsyncImage(
                modifier = Modifier.matchParentSize().clip(CircleShape),
                model = avatarRes,
                placeholder = painterResource(placeholderID),
                contentDescription = null,
                alignment = Alignment.TopCenter,
                contentScale = ContentScale.Crop,
            )
            if (showPushIndicator) {
                HeartRedDot(
                    modifier = Modifier.align(Alignment.TopEnd).offset(x = 4.dp, y = (-4).dp),
                    radius = 8,
                )
            }
        }

        Spacer(Modifier.width(14.dp))

        // 内容区域
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = conversation.agentName,
                    fontSize = 15.sp,
                    lineHeight = 22.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                // Pin 状态图标 - 使用局部变量确保每次重组时读取最新值
                if (isPinned) {
                    Spacer(Modifier.width(6.dp))
                    Image(
                        painter = painterResource(R.drawable.ic_pin),
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                    )
                }
                if (conversation.isDeleted) {
                    Spacer(Modifier.width(4.dp))
                    Text(text = "(deleted)", fontSize = 15.sp, color = Color(0x8CFFFFFF))
                }
            }

            Spacer(Modifier.height(4.dp))
            Text(
                modifier = Modifier.height(22.dp),
                text = conversation.lastMessage,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                color = Color(0x8CFFFFFF),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        // 右侧信息
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            messageCount?.let {
                Text(
                    text = it.toString(),
                    fontSize = 12.sp,
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(2.dp))
            }
            Text(text = conversation.getShowTime(), fontSize = 12.sp, color = Color(0x8CFFFFFF))
        }
        Spacer(Modifier.width(13.dp))
    }
}
