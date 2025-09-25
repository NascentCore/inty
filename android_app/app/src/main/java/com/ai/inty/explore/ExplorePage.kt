package com.ai.inty.explore

import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.beans.AgentInfo
import com.ai.inty.utils.StableCardHeightManager

/** Explore页面 - 推荐agents展示 */
@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("ConfigurationScreenWidthHeight")
@Composable
fun ExplorePage(
    modifier: Modifier = Modifier,
    innerPadding: PaddingValues,
    onClickAgent: (AgentInfo) -> Unit,
    viewModel: ExploreViewModel = viewModel(),
) {
    val context = LocalContext.current

    // 获取Paging数据流
    val agentsFlow = viewModel.getRecommendAgentsFlow()
    val lazyPagingItems = agentsFlow?.collectAsLazyPagingItems()

    // 初始化图片尺寸缓存管理器
    LaunchedEffect(Unit) { StableCardHeightManager.init(context) }

    // 初始化Paging数据
    LaunchedEffect(Unit) { viewModel.initializePagingData() }

    Box(modifier = modifier) {
        IntyImage(modifier = Modifier.align(Alignment.TopEnd), model = R.drawable.notify_header_bg)

        Column(modifier = Modifier.fillMaxSize().background(Color.Transparent)) {
            TopAppBar(
                title = {
                    Image(
                        painter = painterResource(R.drawable.img_explore_title),
                        contentDescription = null,
                        modifier = Modifier.size(132.dp, 28.dp),
                    )
                },
                modifier = Modifier,
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )

            // 使用原生下拉刷新状态
            var isRefreshing by remember { mutableStateOf(false) }

            // 监听Paging的刷新状态，自动控制下拉刷新指示器
            LaunchedEffect(lazyPagingItems?.loadState?.refresh, isRefreshing) {
                when (lazyPagingItems?.loadState?.refresh) {
                    is LoadState.Loading -> {
                        // 正在加载，保持刷新状态
                    }
                    is LoadState.NotLoading -> {
                        if (isRefreshing) {
                            // 刷新完成，隐藏指示器
                            isRefreshing = false
                        }
                    }
                    is LoadState.Error -> {
                        if (isRefreshing) {
                            // 刷新失败，也要隐藏指示器
                            isRefreshing = false
                        }
                    }
                    null -> {
                        // 无数据状态，如果正在刷新则停止
                        if (isRefreshing) {
                            isRefreshing = false
                        }
                    }
                }
            }

            PullToRefreshBox(
                isRefreshing = isRefreshing,
                onRefresh = {
                    isRefreshing = true
                    viewModel.refreshRecommendAgents()
                },
                modifier = Modifier.fillMaxSize(),
            ) {
                ExploreContent(
                    modifier = Modifier.fillMaxSize(),
                    agentsFlow = agentsFlow,
                    innerPadding = innerPadding,
                    onClickAgent = onClickAgent,
                    isRefreshing = isRefreshing,
                )
            }
        }
    }
}
