package com.ai.inty.home

import androidx.compose.foundation.background
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
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.RedDot
import com.ai.inty.beans.ConversationItem
import com.ai.inty.utils.AuthClickable


/**
 * 主页面第二个tab，会话列表页面，包含关注和聊天列表
 */
@Composable
fun ConversationsPage(
    modifier: Modifier,
    conversations: List<ConversationItem>,
    onClickConversationItem: (ConversationItem) -> Unit,
    isLoadingConversations: Boolean = false,
    isRefreshingConversations: Boolean = false,
    onLoadMoreConversations: (() -> Unit)? = null,
) {
    Box(modifier = modifier) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )
        Content(
            conversations = conversations,
            onClickConversationItem = onClickConversationItem,
            isLoadingConversations = isLoadingConversations,
            isRefreshingConversations = isRefreshingConversations,
            onLoadMoreConversations = onLoadMoreConversations,
        )
    }
}

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
        containerColor = Color.Transparent
    ) { innerPadding ->
        Column(modifier = Modifier.fillMaxSize()) {

            Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

            ConversationTabItem(
                modifier = Modifier,
                text = stringResource(R.string.tab_message),
            )

            MessageTabContent(
                conversations = conversations,
                onClickConversationItem = onClickConversationItem,
                isLoading = isLoadingConversations,
                isRefreshing = isRefreshingConversations,
                onLoadMore = onLoadMoreConversations
            )
        }
    }
}


val TAB_ITEM_WIDTH = 120.dp
val TAB_ITEM_HEIGHT = 38.dp
val COLOR_ORANGE = Color(0xFFFF905D)
val COLOR_PURPLE = Color(0xFFC122FF)

@Composable
private fun ConversationTabItem(
    modifier: Modifier,
    text: String,
) {
    Column(modifier = modifier.size(TAB_ITEM_WIDTH, TAB_ITEM_HEIGHT)) {
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
    }
}

/**
 * 消息Tab内容
 */
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
            totalItems > 0 && lastVisibleItem >= totalItems - ACTIVITY_ITEM_BUFFER_COUNT && !isLoading
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
            // 刷新指示器
            if (isRefreshing) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(LOAD_MORE_INDICATOR_HEIGHT),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            color = Color.White,
                            modifier = Modifier.size(24.dp)
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
                    ) { _, conversion ->
                        AuthClickable(onClick = { onClickConversationItem(conversion) }) { authModifier ->
                            ChatHistoryItem(
                                modifier = authModifier.fillMaxWidth(),
                                conversation = conversion
                            )
                        }
                    }
                    item {
                        Spacer(Modifier.height(60.dp))
                    }
                }.onFailure { it.printStackTrace() }
            }

            // 加载更多指示器
            if (isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(LOAD_MORE_INDICATOR_HEIGHT),
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

        if (conversations.isEmpty() && !isLoading && !isRefreshing) {
            EmptyContentUI()
        }
    }
}

val LOAD_MORE_INDICATOR_HEIGHT = 80.dp
val EMPTY_CONTENT_IMAGE_TO_TEXT_PADDING = 16.dp
val EMPTY_CONTENT_TEXT_PADDING_HORIZONTAL = 16.dp
val EMPTY_CONTENT_TEXT_FONT_SIZE = 14.sp

@Composable
private fun EmptyContentUI() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {


        IntyImage(model = R.drawable.group2085655908)

        Spacer(Modifier.height(EMPTY_CONTENT_IMAGE_TO_TEXT_PADDING))

        Text(
            modifier = Modifier
                .padding(horizontal = EMPTY_CONTENT_TEXT_PADDING_HORIZONTAL)
                .align(Alignment.CenterHorizontally),
            text = stringResource(R.string.no_agent),
            color = Color.White.copy(0.55f),
            fontSize = EMPTY_CONTENT_TEXT_FONT_SIZE,
            fontWeight = FontWeight.Normal,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

const val ACTIVITY_ITEM_BUFFER_COUNT = 3


val CHAT_ITEM_HEIGHT = 88.dp
val CHAT_ITEM_PADDING = 16.dp
val CHAT_ITEM_AVATAR_SIZE = 56.dp
val CHAT_ITEM_NAME_HEIGHT = 22.dp
val CHAT_ITEM_NAME_FONT_SIZE = 15.sp
val CHAT_ITEM_LAST_MESSAGE_HEIGHT = 22.dp
val CHAT_ITEM_INITIAL_FOLLOW_DATE_FONT_SIZE = 12.sp
val CHAT_ITEM_NEW_MESSAGE_DOT_HEIGHT = 22.dp
val CHAT_ITEM_DELETED_TEXT_FONT_SIZE = 15.sp
val CHAT_ITEM_NAME_TO_DELETED_TEXT_PADDING = 4.dp
val CHAT_ITEM_DELETED_TEXT_TO_LAST_MESSAGE_PADDING = 4.dp
val CHAT_ITEM_LAST_MESSAGE_TO_INITIAL_FOLLOW_DATE_PADDING = 4.dp
val CHAT_ITEM_INITIAL_FOLLOW_DATE_TO_NEW_MESSAGE_DOT_PADDING = 4.dp
val CHAT_ITEM_NEW_MESSAGE_DOT_TO_RIGHT_PADDING = 13.dp
val CHAT_ITEM_LAST_MESSAGE_FONT_SIZE = 14.sp
val COLOR_SEMI_TRANS_WHITE = Color(0x8CFFFFFF)

@Composable
fun ChatHistoryItem(
    modifier: Modifier,
    conversation: ConversationItem,
    placeholderID: Int = R.drawable.app_icon,
) {
    Row(
        modifier = modifier.height(CHAT_ITEM_HEIGHT),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(Modifier.width(CHAT_ITEM_PADDING))

        // 头像
        IntyImage(
            modifier = Modifier
                .size(CHAT_ITEM_AVATAR_SIZE)
                .clip(RoundedCornerShape(4.dp)),
            model = conversation.agentAvatar,
            placeholder = painterResource(placeholderID)
        )

        Spacer(Modifier.width(CHAT_ITEM_NAME_TO_DELETED_TEXT_PADDING))

        // 内容区域
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    modifier = Modifier.height(CHAT_ITEM_NAME_HEIGHT),
                    text = conversation.agentName,
                    fontSize = CHAT_ITEM_NAME_FONT_SIZE,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (conversation.isDeleted) {
                    Spacer(Modifier.width(CHAT_ITEM_DELETED_TEXT_TO_LAST_MESSAGE_PADDING))
                    Text(
                        text = "(deleted)",
                        fontSize = CHAT_ITEM_DELETED_TEXT_FONT_SIZE,
                        color = COLOR_SEMI_TRANS_WHITE,
                    )
                }
            }

            Spacer(Modifier.height(CHAT_ITEM_LAST_MESSAGE_TO_INITIAL_FOLLOW_DATE_PADDING))
            Text(
                modifier = Modifier.height(CHAT_ITEM_LAST_MESSAGE_HEIGHT),
                text = conversation.lastMessage,
                fontSize = CHAT_ITEM_LAST_MESSAGE_FONT_SIZE,
                color = COLOR_SEMI_TRANS_WHITE,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }

        // 右侧信息
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = conversation.getShowTime(),
                fontSize = CHAT_ITEM_INITIAL_FOLLOW_DATE_FONT_SIZE,
                color = COLOR_SEMI_TRANS_WHITE,
            )
            Spacer(Modifier.height(CHAT_ITEM_INITIAL_FOLLOW_DATE_TO_NEW_MESSAGE_DOT_PADDING))
            Box(
                modifier = Modifier.height(CHAT_ITEM_NEW_MESSAGE_DOT_HEIGHT),
                contentAlignment = Alignment.Center,
            ) {
                if (conversation.isNew) {
                    RedDot()
                }
            }
        }
        Spacer(Modifier.width(CHAT_ITEM_NEW_MESSAGE_DOT_TO_RIGHT_PADDING))
    }
}
