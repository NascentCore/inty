package com.ai.inty.explore

import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.lazy.staggeredgrid.itemsIndexed
import androidx.compose.foundation.lazy.staggeredgrid.rememberLazyStaggeredGridState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.components.ShimmerPlaceholder
import com.ai.inty.ui.components.SmartTagsLayout
import com.ai.inty.utils.ImageSizeCache
import com.ai.inty.utils.getChatBackground
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.delay

/**
 * Explore页面 - 推荐agents展示
 */
@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("ConfigurationScreenWidthHeight")
@Composable
fun ExplorePage(
    modifier: Modifier = Modifier,
    innerPadding: PaddingValues,
    onClickAgent: (AgentInfo) -> Unit,
    viewModel: ExploreViewModel = viewModel()
) {
    val context = LocalContext.current
    val isLoading by viewModel.isLoading.collectAsState()
    val agents = viewModel.agentList

    // 初始化图片尺寸缓存 - 立即同步初始化
    LaunchedEffect(Unit) {
        ImageSizeCache.init(context)
    }

    // 预加载图片尺寸 - 后台异步进行，不影响UI渲染
    LaunchedEffect(agents.isNotEmpty()) {
        if (agents.isNotEmpty()) {
            val imageUrls = agents.mapNotNull { it.getChatBackground() }
            // 后台预加载图片尺寸，不阻塞UI渲染
            ImageSizeCache.preloadImageSizes(imageUrls)
        }
    }

    // 初始化加载数据
    LaunchedEffect(Unit) {
        if (viewModel.agentList.isEmpty()) {
            viewModel.getRecommendAgents()
        }
    }

    Box(modifier = modifier) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent)
        ) {
            TopAppBar(
                title = {
                    Image(
                        painter = painterResource(R.drawable.img_explore_title),
                        contentDescription = null,
                        modifier = Modifier.size(132.dp, 28.dp)
                    )
                },
                modifier = Modifier,
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent)
            )

            // 使用原生下拉刷新状态
            var isRefreshing by remember { mutableStateOf(false) }

            // 监听加载状态变化，刷新完成时重置状态
            LaunchedEffect(isLoading) {
                if (!isLoading && isRefreshing) {
                    isRefreshing = false
                }
            }

            PullToRefreshBox(
                isRefreshing = isRefreshing,
                onRefresh = {
                    isRefreshing = true
                    viewModel.refreshRecommendAgents()
                },
                modifier = Modifier.fillMaxSize()
            ) {
                val gridState = rememberLazyStaggeredGridState(
                    initialFirstVisibleItemIndex = 0,
                    initialFirstVisibleItemScrollOffset = 0
                )

                // 检测是否滚动到底部 - 使用更稳定的计算方式
                val reachedBottom by remember {
                    derivedStateOf {
                        val layoutInfo = gridState.layoutInfo
                        val totalItemsCount = layoutInfo.totalItemsCount
                        val lastVisibleItemIndex =
                            layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1

                        // 更严格的底部检测逻辑，避免首次进入时误触发
                        // 只有在用户真正滚动到底部时才触发加载更多
                        val isScrolledToBottom = totalItemsCount > 0 &&
                                lastVisibleItemIndex >= totalItemsCount - 1 && // 更严格：必须是最后一个item可见
                                totalItemsCount >= 10 && // 确保至少有10个项目
                                gridState.firstVisibleItemIndex > 0 // 确保用户已经滚动过（不是初始状态）

                        isScrolledToBottom
                    }
                }

                // 触发加载更多，添加防抖机制和稳定性检查
                LaunchedEffect(reachedBottom, agents.size) {
                    if (reachedBottom && agents.isNotEmpty() && !isLoading) {
                        // 增加延迟，避免快速滚动和布局变化时重复触发
                        delay(300)
                        // 再次检查状态，确保在延迟期间状态没有变化
                        // 额外检查：确保不是首次进入页面（通过检查滚动状态）
                        if (reachedBottom && agents.isNotEmpty() && !isLoading && gridState.firstVisibleItemIndex > 0) {
                            viewModel.loadMoreRecommendAgents()
                        }
                    }
                }

                LazyVerticalStaggeredGrid(
                    columns = StaggeredGridCells.Fixed(2),
                    modifier = Modifier.padding(bottom = innerPadding.calculateBottomPadding()),
                    state = gridState,
                    contentPadding = PaddingValues(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalItemSpacing = 8.dp,
                ) {
                    runCatching {
                        if (agents.isNotEmpty()) {
                            //记录重复数据
                            listDup(agents)
                            //UI渲染
                            itemsIndexed(
                                items = agents,
                                key = { _, agent -> agent.id } // 使用稳定的 ID 作为 key
                            ) { _, agent ->
                                CharacterCard(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(8.dp))
                                        .noRippleClickable {
                                            onClickAgent(agent)
                                        },
                                    agentInfo = agent,
                                )
                            }
                        }
                    }.onFailure { it.printStackTrace() }

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
                        Spacer(Modifier.height(16.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun CharacterCard(
    modifier: Modifier = Modifier,
    agentInfo: AgentInfo,
) {
    val density = LocalDensity.current

    // 缓存渐变画笔，避免每次重组时重新创建
    val gradientBrush = remember {
        Brush.verticalGradient(
            colors = listOf(
                Color.Transparent,
                Color.Black.copy(.5f),
                Color.Black.copy(.9f),
            )
        )
    }

    // 缓存过滤后的标签，避免每次重组时重新计算
    val filteredTags = remember(agentInfo.tags) {
        agentInfo.tags?.filterNotNull() ?: emptyList()
    }

    // 获取图片URL
    val imageUrl = remember(agentInfo.id, agentInfo.background, agentInfo.avatar) {
        agentInfo.getChatBackground()
    }

    // 动态计算卡片高度，基于图片宽高比
    // 暂时使用固定高度确保UI正常显示，避免黑屏问题
    val cardHeight = remember(imageUrl) {
        // 先使用固定高度，确保UI能正常显示
        val heightPx = ImageSizeCache.getDisplayHeightPx(imageUrl)
        with(density) { heightPx.toDp() }
    }

    // 图片加载状态
    var imageLoaded by remember { mutableStateOf(false) }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(cardHeight) // 等图片尺寸缓存稳定后再启用
    ) {
        // 背景图片层
        Box(modifier = Modifier.fillMaxSize()) {
            // 使用 Shimmer 占位符
            if (!imageLoaded) {
                ShimmerPlaceholder(
                    modifier = Modifier.fillMaxSize(),
                    cornerRadius = 8.dp
                )
            }

            IntyImage(
                modifier = Modifier.fillMaxSize(),
                model = imageUrl,
                contentScale = ContentScale.Crop,
                onSuccess = {
                    imageLoaded = true
                },
                onError = {
                    imageLoaded = false
                }
            )
        }

        // 文本内容层 - 立即显示，不依赖图片加载状态
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(brush = gradientBrush)
                .padding(start = 8.dp, end = 8.dp, top = 16.dp, bottom = 8.dp)
                .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                modifier = Modifier,
                text = agentInfo.name,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )

            Text(
                modifier = Modifier,
                text = agentInfo.intro,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                fontWeight = FontWeight.Normal,
                color = Color(0xB2FFFFFF),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )

            if (filteredTags.isNotEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(16.dp)
                ) {
                    SmartTagsLayout(
                        modifier = Modifier.matchParentSize(),
                        tags = filteredTags,
                        isCardTag = true
                    )
                }
            }
        }
    }
}

private fun listDup(agents: List<AgentInfo>) {
    if (agents.isEmpty()) return

    // 用于存储已见过的组合，key为"name|id|avatar"的组合
    val seenCombinations = mutableSetOf<String>()
    val duplicateItems = mutableListOf<AgentInfo>()

    agents.forEach { agent ->
        // 创建唯一标识符：name|id|avatar
        val combination = "${agent.name}|${agent.id}|${agent.avatar}"

        if (seenCombinations.contains(combination)) {
            // 发现重复项
            duplicateItems.add(agent)
        } else {
            seenCombinations.add(combination)
        }
    }

    // 输出统计信息
    EasyLog.log(
        "Explore测试，listDup统计: 总数量=${agents.size}, 重复数量=${duplicateItems.size}, 唯一数量=${agents.size - duplicateItems.size}",
        EasyLog.INFO
    )

    // 如果有重复项，输出详细信息
    if (duplicateItems.isNotEmpty()) {
        EasyLog.log("Explore测试，重复项详细信息:", EasyLog.WARN)
        duplicateItems.forEachIndexed { index, agent ->
            EasyLog.log(
                "Explore测试，重复项${index + 1}: name='${agent.name}', id='${agent.id}', avatar='${agent.avatar}'",
                EasyLog.WARN
            )
        }
    }
}
