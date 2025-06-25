package com.ai.inty.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.utils.AuthClickable

@Composable
fun RecommendPage(
    modifier: Modifier,
    agents: List<AgentInfo>,
    isLoading: Boolean = false,
    onClickAgent: (AgentInfo) -> Unit,
    onLoadMore: () -> Unit = {},
) {
//    val agents = viewModel.agentList
    Box(
        modifier = modifier
    ) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )
        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent
        ) { innerPadding ->

            Column {
                Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

                Row(
                    modifier = Modifier.padding(24.dp, 0.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IntyImage(
                        model = R.drawable.popular1
                    )
                    Spacer(Modifier.width(7.dp))
                    IntyImage(
                        model = R.drawable.popular
                    )
                }

                Spacer(Modifier.height(30.dp))

                val gridState = rememberLazyGridState()
                
                // 检测是否滚动到底部
                val reachedBottom = remember {
                    derivedStateOf {
                        val lastVisibleItem = gridState.layoutInfo.visibleItemsInfo.lastOrNull()
                        lastVisibleItem?.index != null && lastVisibleItem.index >= agents.size - 3
                    }
                }
                
                // 触发加载更多
                LaunchedEffect(reachedBottom.value) {
                    if (reachedBottom.value && agents.isNotEmpty() && !isLoading) {
                        onLoadMore()
                    }
                }

                LazyVerticalGrid(
                    state = gridState,
                    modifier = Modifier.padding(bottom = innerPadding.calculateBottomPadding(), start = 16.dp, end = 16.dp),
                    columns = GridCells.Fixed(2),
                    horizontalArrangement = Arrangement.spacedBy(13.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    items(agents) { agent ->
                        AuthClickable(
                            onClick = {
                                onClickAgent(agent)
                            }
                        ) { authModifier ->
                            RecommendPageItem(
                                modifier = authModifier.size(165.dp, 220.dp),
                                agentInfo = agent
                            )
                        }
                    }

                    // 加载更多指示器
                    if (isLoading && agents.isNotEmpty()) {
                        item {
                            Box(
                                modifier = Modifier
                                    .size(165.dp, 60.dp)
                                    .padding(16.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(24.dp),
                                    color = Color.White.copy(0.7f)
                                )
                            }
                        }
                    }
                    
                    item {
                        Spacer(Modifier.height(100.dp))
                    }
                }
            }


        }
    }
}

@Composable
fun RecommendPageItem(
    modifier: Modifier,
    agentInfo: AgentInfo
) {
    Box(
        modifier = modifier.size(165.dp, 220.dp)
    ) {
        IntyImage(
            modifier = Modifier.fillMaxSize(),
            model = agentInfo.avatar,
            placeholder = painterResource(R.drawable.app_2),
            error = painterResource(R.drawable.app_2),
        )
        Text(
            modifier = Modifier.align(Alignment.BottomStart).padding(12.dp),
            text = agentInfo.name,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
    }
}
