package com.ai.inty.newchat.ui.screens

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.ai.inty.newchat.data.ChatDataManager
import com.ai.inty.newchat.ui.components.ChatPage
import com.ai.inty.newchat.viewmodel.ChatTabViewModel

/**
 * Chat Tab页面
 * 包含HorizontalPager，每个页面是一个Agent的聊天界面
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun ChatTabScreen(
    modifier: Modifier = Modifier,
    chatTabViewModel: ChatTabViewModel,
    chatDataManager: ChatDataManager
) {
    val agents by chatTabViewModel.agents.collectAsState()
    val isLoading by chatTabViewModel.isLoading.collectAsState()
    val error by chatTabViewModel.error.collectAsState()
    val currentPage by chatTabViewModel.currentPage.collectAsState()

    if (isLoading) {
        Box(
            modifier = modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator()
        }
    } else if (error != null) {
        Box(
            modifier = modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = error ?: "加载失败",
                color = MaterialTheme.colorScheme.error
            )
        }
    } else if (agents.isEmpty()) {
        Box(
            modifier = modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "暂无Agent",
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }
    } else {
        val pagerState = rememberPagerState(
            initialPage = currentPage,
            pageCount = { agents.size }
        )

        // 监听页面变化，更新ViewModel状态
        LaunchedEffect(pagerState.currentPage) {
            chatTabViewModel.setCurrentPage(pagerState.currentPage)
        }

        HorizontalPager(
            state = pagerState,
            modifier = modifier.fillMaxSize(),
            beyondViewportPageCount = 3
        ) { pageIndex ->
            val agent = agents[pageIndex]
            // 从ChatTabViewModel获取或创建ChatViewModel实例，确保实例持久化
            val chatViewModel = chatTabViewModel.getChatViewModel(agent.id)

            ChatPage(
                agentId = agent.id,
                agentName = agent.name,
                modifier = Modifier.fillMaxSize(),
                chatViewModel = chatViewModel,
                chatDataManager = chatDataManager,
                isCurrentPage = pageIndex == pagerState.currentPage
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
fun ChatTabScreenPreview() {
    MaterialTheme {
        // 预览需要模拟的ViewModel，这里简化处理
        Text("ChatTabScreen Preview")
    }
}
