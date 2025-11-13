package com.ai.intellimate.explore

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.startup.ImagePreloadManager
import ai.sxwl.android.data.api.model.AgentInfo
import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import kotlinx.coroutines.delay

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

    // 使用 PageTrackingHelper 进行页面跟踪
    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView(
            "ExplorePage",
            "MainActivity",
            mapOf(
                "agent_count" to (lazyPagingItems?.itemCount ?: 0),
                "is_loading" to (lazyPagingItems?.loadState?.refresh is LoadState.Loading),
            ),
        )
    }

    // 初始化图片尺寸缓存管理器和图片预加载管理器
    LaunchedEffect(Unit) { ImagePreloadManager.init(context) }

    // 初始化Paging数据
    LaunchedEffect(Unit) { viewModel.initializePagingData() }

    Box(modifier = modifier) {
        AsyncImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg,
            contentDescription = null,
        )

        Column(modifier = Modifier.fillMaxSize().background(Color.Transparent)) {
            TopAppBar(
                title = {
                    Image(
                        painter = painterResource(R.drawable.img_explore_title),
                        contentDescription = null,
                        modifier = Modifier.height(30.dp).fillMaxWidth(),
                        contentScale = ContentScale.Fit,
                        alignment = Alignment.CenterStart,
                    )
                },
                modifier = Modifier,
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )

            // 使用原生下拉刷新状态
            var isRefreshing by remember { mutableStateOf(false) }
            var refreshStartTime by remember { mutableLongStateOf(0L) }

            // 监听Paging的刷新状态，自动控制下拉刷新指示器
            // 添加最小持续时间（400ms），避免快速完成时的闪动
            LaunchedEffect(lazyPagingItems?.loadState?.refresh, isRefreshing) {
                val currentTime = System.currentTimeMillis()
                val minRefreshDuration = 400L // 最小刷新持续时间（毫秒）
                val elapsedTime = if (refreshStartTime > 0) currentTime - refreshStartTime else 0L

                when (lazyPagingItems?.loadState?.refresh) {
                    is LoadState.Loading -> {
                        // 正在加载，保持刷新状态
                        // 如果 refreshStartTime 未设置且正在刷新，则设置开始时间
                        if (isRefreshing && refreshStartTime == 0L) {
                            refreshStartTime = currentTime
                        }
                    }

                    is LoadState.NotLoading -> {
                        if (isRefreshing) {
                            // 刷新完成，但确保至少显示最小持续时间
                            if (elapsedTime >= minRefreshDuration) {
                                isRefreshing = false
                                refreshStartTime = 0L
                            } else {
                                // 延迟到最小持续时间后再隐藏
                                delay(minRefreshDuration - elapsedTime)
                                isRefreshing = false
                                refreshStartTime = 0L
                            }
                        }
                    }

                    is LoadState.Error -> {
                        if (isRefreshing) {
                            // 刷新失败，也要隐藏指示器，但确保至少显示最小持续时间
                            if (elapsedTime >= minRefreshDuration) {
                                isRefreshing = false
                                refreshStartTime = 0L
                            } else {
                                delay(minRefreshDuration - elapsedTime)
                                isRefreshing = false
                                refreshStartTime = 0L
                            }
                        }
                    }

                    null -> {
                        // 无数据状态，如果正在刷新则停止
                        if (isRefreshing) {
                            if (elapsedTime >= minRefreshDuration) {
                                isRefreshing = false
                                refreshStartTime = 0L
                            } else {
                                delay(minRefreshDuration - elapsedTime)
                                isRefreshing = false
                                refreshStartTime = 0L
                            }
                        }
                    }
                }
            }

            PullToRefreshBox(
                isRefreshing = isRefreshing,
                onRefresh = {
                    // 设置刷新开始时间
                    refreshStartTime = System.currentTimeMillis()
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
                    onRetry = { viewModel.refreshRecommendAgents() },
                )
            }
        }
    }
}
