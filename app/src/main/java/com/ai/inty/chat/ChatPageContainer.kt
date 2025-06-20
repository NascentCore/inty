package com.ai.inty.chat

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.viewmodels.ChatViewModel

@Composable
fun ChatPageContainer(
    modifier: Modifier,
    viewModelFactory: ViewModelProvider.Factory,
    agentList: List<AgentInfo>,
) {
    val pageState = rememberPagerState {
        agentList.size
    }
    HorizontalPager(
        modifier = modifier,
        state = pageState,
    ) { currentPage ->

        val agent = agentList.get(currentPage)

        val chatViewModel: ChatViewModel = viewModel(
            key = agent.id,
            factory = viewModelFactory
        )

        LaunchedEffect(key1 = agent.id) {
            chatViewModel.setAgentInfo(agent)
        }

        ChatPage(
            modifier = Modifier.fillMaxSize(),
            chatViewModel = chatViewModel,
        )
    }

}