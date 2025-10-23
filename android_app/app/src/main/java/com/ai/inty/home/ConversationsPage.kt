package com.ai.inty.home

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
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
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.RedDot
import com.ai.inty.beans.ConversationItem
import com.ai.inty.ui.components.EmptyDataState
import com.ai.inty.utils.AuthClickable
import com.ai.inty.utils.TrackScreenView
import com.ai.inty.utils.getCdnImageUrl

/** 主页面第二个tab，会话列表页面，包含关注和聊天列表 */
@Composable
fun ConversationsPage(
    modifier: Modifier,
    conversations: List<ConversationItem>,
    onClickConversationItem: (ConversationItem) -> Unit,
    isLoadingConversations: Boolean = false,
    isRefreshingConversations: Boolean = false,
    onLoadMoreConversations: (() -> Unit)? = null,
) {
    // 跟踪ConversationsPage页面访问
    TrackScreenView(
        screenName = "ConversationsPage",
        screenClass = "MainActivity",
        additionalParams =
            mapOf(
                "conversation_count" to conversations.size,
                "is_loading" to isLoadingConversations,
            ),
    )

    Box(modifier = modifier) {
        IntyImage(modifier = Modifier.align(Alignment.TopEnd), model = R.drawable.notify_header_bg)
        Content(
            conversations = conversations,
            onClickConversationItem = onClickConversationItem,
            isLoadingConversations = isLoadingConversations,
            isRefreshingConversations = isRefreshingConversations,
            onLoadMoreConversations = onLoadMoreConversations,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Content(
    conversations: List<ConversationItem>,
    onClickConversationItem: (ConversationItem) -> Unit,
    isLoadingConversations: Boolean = false,
    isRefreshingConversations: Boolean = false,
    onLoadMoreConversations: (() -> Unit)? = null,
) {
    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Transparent),
        containerColor = Color.Transparent,
        topBar = {
            TopAppBar(
                title = {
                    Image(
                        painter = painterResource(R.drawable.img_message_title),
                        contentDescription = null,
                        modifier =
                            Modifier
                                .height(30.dp)
                                .fillMaxWidth(),
                        contentScale = ContentScale.Fit,
                        alignment = Alignment.CenterStart,
                    )
                },
                modifier = Modifier,
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            MessageTabContent(
                conversations = conversations,
                onClickConversationItem = onClickConversationItem,
                isLoading = isLoadingConversations,
                isRefreshing = isRefreshingConversations,
                onLoadMore = onLoadMoreConversations,
            )
        }
    }
}

/** 消息Tab内容 */
@Composable
private fun MessageTabContent(
    conversations: List<ConversationItem>,
    onClickConversationItem: (ConversationItem) -> Unit,
    isLoading: Boolean = false,
    isRefreshing: Boolean = false,
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
        LazyColumn(state = listState, modifier = Modifier.matchParentSize()) {
            // 刷新指示器
            if (isRefreshing) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(80.dp),
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
            if (conversations.isNotEmpty()) {
                runCatching {
                    itemsIndexed(
                        items = conversations,
                        key = { index, conversion -> "${conversion.agentId}_$index" },
                    ) { _, conversion ->
                        AuthClickable(onClick = { onClickConversationItem(conversion) }) { authModifier ->
                            ChatHistoryItem(
                                modifier = authModifier.fillMaxWidth(),
                                conversation = conversion,
                            )
                        }
                    }
                    item { Spacer(Modifier.height(60.dp)) }
                }
                    .onFailure { it.printStackTrace() }
            }

            // 加载更多指示器
            if (isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(80.dp),
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

        if (conversations.isEmpty() && !isLoading && !isRefreshing) {
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
        IntyImage(
            modifier = Modifier
                .size(56.dp)
                .clip(CircleShape),
            model = getCdnImageUrl(conversation.agentAvatar, width = 128),
            placeholder = painterResource(placeholderID),
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
                    RedDot()
                }
            }
        }
        Spacer(Modifier.width(13.dp))
    }
}
