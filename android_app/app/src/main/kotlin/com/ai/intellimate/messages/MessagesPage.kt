package com.ai.intellimate.messages

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.design.ui.HeartRedDot
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.EmptyDataState

/** 主页面第二个tab，会话列表页面，包含关注和聊天列表 */
@Composable
fun MessagesPage(
    modifier: Modifier = Modifier,
    viewModel: MessagesViewModel,
    onClickConversationItem: (ConversationItem) -> Unit,
    pageTrackingContext: String = "MessagesPage",
) {
    val uiState by viewModel.uiState.collectAsState()

    // 页面跟踪（首次加载时）
    LaunchedEffect(pageTrackingContext) { viewModel.trackPageView(pageTrackingContext) }

    // 监听会话列表更新，检查是否有新消息自动取消隐藏
    LaunchedEffect(uiState.conversations) { viewModel.checkAndUnhideConversations() }

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
) {
    val listState = rememberLazyListState()

    // 检测滚动到底部
    val shouldLoadMore by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val totalItems = layoutInfo.totalItemsCount
            val lastVisibleItem = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0

            // 当滚动到倒数第3项时触发加载更多
            totalItems > 0 &&
                lastVisibleItem >= totalItems - 3 &&
                !uiState.isLoading &&
                uiState.hasMore
        }
    }

    // 监听滚动状态，触发加载更多
    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore) {
            onLoadMore()
        }
    }

    // 菜单状态（移到 LazyColumn 外部）
    var showMenuForConversationId by remember { mutableStateOf<String?>(null) }
    var menuItemIndex by remember { mutableStateOf(-1) }

    Box(Modifier.fillMaxSize()) {
        LazyColumn(state = listState, modifier = Modifier.matchParentSize()) {
            // 刷新指示器
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

            // 会话列表
            if (uiState.conversations.isNotEmpty()) {
                runCatching {
                        itemsIndexed(
                            items = uiState.conversations,
                            key = { index, conversion -> "${conversion.agentId}_$index" },
                        ) { index, conversion ->
                            var lastClickTime by remember { mutableStateOf(0L) }

                            // 使用 combinedClickable 同时处理点击和长按
                            Box(
                                modifier =
                                    Modifier.fillMaxWidth()
                                        .combinedClickable(
                                            onClick = {
                                                // 正常点击：如果菜单未显示，则进入聊天
                                                if (
                                                    showMenuForConversationId != conversion.agentId
                                                ) {
                                                    val currentTime = System.currentTimeMillis()
                                                    if (AntiClick.isValidClick(lastClickTime)) {
                                                        lastClickTime = currentTime
                                                        // 检查是否已登录
                                                        if (
                                                            IntySetting.isLogin() &&
                                                                IntySetting.getCurToken()
                                                                    .isNotEmpty()
                                                        ) {
                                                            onClickConversationItem(conversion)
                                                        }
                                                    }
                                                } else {
                                                    // 如果菜单显示，点击则关闭菜单
                                                    showMenuForConversationId = null
                                                }
                                            },
                                            onLongClick = {
                                                // 长按：显示菜单，记录 item 索引用于定位
                                                showMenuForConversationId = conversion.agentId
                                                menuItemIndex = index
                                            },
                                        )
                            ) {
                                ChatHistoryItem(
                                    modifier = Modifier.fillMaxWidth(),
                                    conversation = conversion,
                                )
                            }
                        }
                        item { Spacer(Modifier.height(60.dp)) }
                    }
                    .onFailure { it.printStackTrace() }
            }

            // 加载更多指示器
            if (uiState.isLoading) {
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
        }

        // 显示菜单（在 LazyColumn 外部）
        if (showMenuForConversationId != null) {
            val conversation =
                uiState.conversations.find { it.agentId == showMenuForConversationId }
            conversation?.let { conv ->
                // 遮罩层，点击外部关闭菜单（全屏）
                Box(
                    modifier =
                        Modifier.fillMaxSize()
                            .background(Color.Transparent)
                            .clickable { showMenuForConversationId = null }
                            .zIndex(999f)
                )

                // 菜单内容（显示在 item 位置附近）
                // 计算菜单位置：基于 item 索引估算位置
                val estimatedItemHeight = 88.dp
                val menuY = (estimatedItemHeight * menuItemIndex) + estimatedItemHeight / 2

                Box(
                    modifier = Modifier.fillMaxSize().zIndex(1000f),
                    contentAlignment = Alignment.TopStart,
                ) {
                    ConversationItemMenu(
                        conversation = conv,
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
                        modifier = Modifier.offset(x = 16.dp, y = menuY).width(140.dp),
                    )
                }
            }
        }

        if (uiState.conversations.isEmpty() && !uiState.isLoading && !uiState.isRefreshing) {
            EmptyDataState(
                subtitle = stringResource(R.string.empty_conversations),
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

@Composable
private fun ChatHistoryItem(
    modifier: Modifier,
    conversation: ConversationItem,
    placeholderID: Int = R.drawable.img_default_avatar,
) {
    Row(modifier = modifier.height(88.dp), verticalAlignment = Alignment.CenterVertically) {
        Spacer(Modifier.width(16.dp))

        // 头像
        AsyncImage(
            modifier = Modifier.size(56.dp).clip(CircleShape),
            model = getCdnImageUrl(conversation.agentAvatar, width = 128),
            placeholder = painterResource(placeholderID),
            contentDescription = null,
            alignment = Alignment.TopCenter,
            contentScale = ContentScale.Crop,
        )

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
                // Pin 状态图标
                if (conversation.isPinned) {
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
            Text(text = conversation.getShowTime(), fontSize = 12.sp, color = Color(0x8CFFFFFF))
            Spacer(Modifier.height(4.dp))
            Box(modifier = Modifier.height(22.dp), contentAlignment = Alignment.Center) {
                if (conversation.isNew) {
                    HeartRedDot()
                }
            }
        }
        Spacer(Modifier.width(13.dp))
    }
}
