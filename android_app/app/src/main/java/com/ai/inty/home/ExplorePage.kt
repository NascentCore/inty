package com.ai.inty.home

import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
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
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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


@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("ConfigurationScreenWidthHeight")
@Composable
fun ExplorePage(
    modifier: Modifier,
    innerPadding: PaddingValues,
    agents: List<AgentInfo>,
    isLoading: Boolean = false,
    onClickAgent: (AgentInfo) -> Unit,
    onLoadMore: () -> Unit = {},
    onRefresh: () -> Unit = {},
) {
    val context = LocalContext.current

    // 初始化图片尺寸缓存
    LaunchedEffect(Unit) {
        ImageSizeCache.init(context)
    }

    // 预加载图片尺寸 - 立即执行，不等待 agents 变化
    LaunchedEffect(agents.isNotEmpty()) {
        if (agents.isNotEmpty()) {
            val imageUrls = agents.mapNotNull { it.getChatBackground() }
            ImageSizeCache.preloadImageSizes(imageUrls)
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
                    onRefresh()
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

                        // 当最后一个可见项接近列表末尾时触发加载更多
                        totalItemsCount > 0 && lastVisibleItemIndex >= totalItemsCount - 3
                    }
                }

                // 触发加载更多，添加防抖机制
                LaunchedEffect(reachedBottom, agents.size) {
                    if (reachedBottom && agents.isNotEmpty() && !isLoading) {
                        // 添加延迟，避免快速滚动时重复触发
                        delay(200)
                        onLoadMore()
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
fun CharacterCard(
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

    // 缓存文本内容，确保稳定显示
    val agentName = remember(agentInfo.name) { agentInfo.name }
    val agentIntro = remember(agentInfo.intro) { agentInfo.intro }

    // 动态计算卡片高度，基于图片宽高比
    val cardHeight = remember(imageUrl) {
        val heightPx = ImageSizeCache.getDisplayHeightPx(imageUrl)
        with(density) { heightPx.toDp() }
    }

    // 图片加载状态
    var imageLoaded by remember { mutableStateOf(false) }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .aspectRatio(.6f)
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
                modifier = Modifier
                    .fillMaxSize(),
                model = imageUrl,
                contentScale = ContentScale.Crop,
                placeholder = null, // 使用自定义的 Shimmer 占位符
                error = null, // 错误时也使用 Shimmer
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
                text = agentName,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )

            Text(
                modifier = Modifier,
                text = agentIntro,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                fontWeight = FontWeight.Normal,
                color = Color(0xB2FFFFFF),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )

            if (filteredTags.isNotEmpty()) {
                Box(modifier = Modifier
                    .fillMaxWidth()
                    .height(16.dp)) {
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

@Preview(showBackground = true)
@Composable
fun CharacterCardPreview() {
    CharacterCard(
        agentInfo = AgentInfo(
            id = "test_id",
            name = "测试角色",
            intro = "这是一个测试角色的介绍，用来展示卡片的效果",
            avatar = "https://example.com/avatar.jpg",
            background = "https://example.com/background.jpg",
            tags = listOf("标签1", "标签2", "标签3")
        )
    )
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
