package com.ai.intellimate.chat.ui.screens

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.ai.intellimate.chat.NewChatActivity
import com.ai.intellimate.chat.ui.components.AgentCard
import com.ai.intellimate.chat.viewmodel.ExploreViewModel

/**
 * Explore Tab页面
 * 显示Agent列表，点击可进入聊天
 */
@Composable
fun ExploreTabScreen(
    modifier: Modifier = Modifier,
    exploreViewModel: ExploreViewModel
) {
    val context = LocalContext.current
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
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    text = error ?: "加载失败",
                    color = MaterialTheme.colorScheme.error
                )
            }
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
        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            state = rememberLazyGridState(),
            modifier = modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(
                items = agents,
                key = { it.id }
            ) { agent ->
                AgentCard(
                    agent = agent,
                    onClick = {
                        val intent = Intent(
                            context,
                            NewChatActivity::class.java
                        )
                        intent.putExtra("agent_id", agent.id)
                        intent.putExtra("agent_name", agent.name)
                        context.startActivity(intent)
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(.75f)
                )
            }
        }
    }
}
