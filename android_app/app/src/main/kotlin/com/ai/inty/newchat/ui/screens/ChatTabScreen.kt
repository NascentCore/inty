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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.ai.inty.newchat.data.ChatDataManager
import com.ai.inty.newchat.ui.components.ChatPage
import com.ai.inty.newchat.viewmodel.ChatViewModel
import com.ai.inty.newchat.viewmodel.ExploreViewModel
import com.ai.inty.newchat.viewmodel.GlobalChatViewModel

/**
 * Chat Tab页面
 * 包含HorizontalPager，每个页面是一个Agent的聊天界面
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun ChatTabScreen(
    modifier: Modifier = Modifier,
    exploreViewModel: ExploreViewModel,
    globalChatViewModel: GlobalChatViewModel,
    chatDataManager: ChatDataManager
) {
    val agents by exploreViewModel.agents.collectAsState()
    val isLoading by exploreViewModel.isLoading.collectAsState()
    val error by exploreViewModel.error.collectAsState()

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
            initialPage = 0,
            pageCount = { agents.size }
        )

        HorizontalPager(
            state = pagerState,
            modifier = modifier.fillMaxSize()
        ) { pageIndex ->
            val agent = agents[pageIndex]
            // 暂时直接创建ChatViewModel，避免ViewModelProvider的复杂性
            val chatViewModel = remember { ChatViewModel(globalChatViewModel, chatDataManager) }

            ChatPage(
                agentId = agent.id,
                agentName = agent.name,
                modifier = Modifier.fillMaxSize(),
                chatViewModel = chatViewModel
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
