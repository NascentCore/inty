package com.ai.inty.chat

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.animateScrollBy
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.PagerState
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.paging.compose.collectAsLazyPagingItems
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.UserProfile
import com.ai.inty.chat.viewmodel.ChatTabViewModel
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * ChatPageContainer - 支持分页加载的聊天页面容器
 * 使用Paging库实现分页加载更多agents，提供更流畅的滑动体验
 */
@Composable
fun ChatPageContainer(
    modifier: Modifier,
    viewModelFactory: ViewModelProvider.Factory,
    chatTabViewModel: ChatTabViewModel,
    userProfile: UserProfile,
    currentPageIndex: Int = 0,
    onPageChanged: (Int) -> Unit = {},
) {
    // 获取Paging数据流
    val agentsFlow = chatTabViewModel.getChatAgentsFlow()
    val agentsPagingItems = agentsFlow?.collectAsLazyPagingItems() ?: return

    // 获取当前加载的agents列表
    val agentList = remember(agentsPagingItems.itemCount) {
        val list = mutableListOf<AgentInfo>()
        for (i in 0 until agentsPagingItems.itemCount) {
            agentsPagingItems[i]?.let { agent ->
                list.add(agent)
            }
        }
        list
    }

    // 如果 agentList 为空，显示空状态
    if (agentList.isEmpty()) {
        Box(
            modifier = modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            // 可以在这里显示加载中或空状态的UI
            // 暂时显示空白，等待数据加载
        }
        return
    }

    // 防止初始页面索引越界
    val safeInitialPage = if (currentPageIndex >= 0 && currentPageIndex < agentList.size) {
        currentPageIndex
    } else {
        0 // 默认使用第一页
    }
    val pageState = rememberPagerState(initialPage = safeInitialPage) { agentList.size }
    val scope = rememberCoroutineScope()

    // 新用户引导状态
    var hasShowGuest by remember { mutableStateOf(IntySetting.hasShowGuest()) }
    val shouldShowGuide = remember(agentList.size, hasShowGuest) {
        !hasShowGuest && agentList.size > 1
    }

    // 监听页面变化
    LaunchedEffect(pageState.currentPage) {
        onPageChanged(pageState.currentPage)

        // 页面切换时停止当前播放的音频，避免播放错误agent的音频
        val currentAgent = agentList.getOrNull(pageState.currentPage)
        if (currentAgent != null) {
            try {
                val audioManager = com.ai.inty.audio.AudioManager.getInstance(
                    com.inty.utils.AppEnv.context,
                    scope
                )
                audioManager.stopAllPlayback()
            } catch (e: Exception) {
                EasyLog.log("ChatPageContainer - 停止音频播放失败: ${e.message}", EasyLog.ERROR)
            }
            delay(100)
        }

        // 预加载逻辑：当用户接近最后一页时，触发加载更多数据
        val currentPage = pageState.currentPage
        val totalPages = agentList.size
        if (currentPage >= totalPages - 2 && totalPages > 0) {
            agentsPagingItems.retry()
        }
    }

    // 监听Paging数据变化，更新页面状态
    LaunchedEffect(agentsPagingItems.itemCount) {
        // Paging数据更新时会自动触发UI重组
    }

    Box {
        HorizontalPager(
            modifier = modifier,
            state = pageState,
            userScrollEnabled = !shouldShowGuide, // 在引导期间禁用用户滑动
        ) { currentPage ->
            // 防止数组越界
            if (currentPage < 0 || currentPage >= agentList.size) {
                // 如果索引无效，显示空页面或返回
                return@HorizontalPager
            }
            val agent = agentList[currentPage]
            val chatViewModel: ChatViewModel = viewModel(
                key = agent.id,
                factory = viewModelFactory
            )

            LaunchedEffect(key1 = agent.id, key2 = agent.isFollowed) {
                chatViewModel.setAgentInfo(agent)
                chatViewModel.setUserProfile(userProfile)
            }

            ChatPage(
                modifier = Modifier.fillMaxSize(),
                chatViewModel = chatViewModel,
                isCurrentPage = currentPage == pageState.currentPage
            )
        }

        // 加载状态指示器
        if (agentsPagingItems.loadState.append is androidx.paging.LoadState.Loading) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(16.dp)
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    strokeWidth = 2.dp
                )
            }
        }
        
        // 新用户聊天滑动引导
        NewUserGuide(
            agentList = agentList,
            pageState = pageState,
            shouldShowGuide = shouldShowGuide,
            onGuideCompleted = { hasShowGuest = true }
        )

    }
}

/**
 * 新用户引导组件
 */
@Composable
private fun NewUserGuide(
    agentList: List<AgentInfo>,
    pageState: PagerState,
    shouldShowGuide: Boolean,
    onGuideCompleted: () -> Unit,
) {

    if (shouldShowGuide) {
        val density = LocalDensity.current
        val pageScrollPx = with(density) { 80.dp.toPx() }
        var showHand by remember { mutableStateOf(false) }
        var isGuideActive by remember { mutableStateOf(false) }
        // 保存初始页面索引，确保能正确恢复
        val initialPageIndex = remember { pageState.currentPage }

        LaunchedEffect(Unit) {
            delay(3000)
            isGuideActive = true
            showHand = true
            pageState.animateScrollBy(pageScrollPx)
            delay(1000)
            showHand = false
            pageState.animateScrollToPage(initialPageIndex)
            IntySetting.setShowGuested()
            onGuideCompleted()
            isGuideActive = false
        }

        AnimatedVisibility(
            visible = showHand,
            enter = fadeIn() + slideInHorizontally(
                initialOffsetX = { fullWidth -> fullWidth / 6 } // 从屏幕右侧1/6处出现
            ),
            exit = fadeOut(targetAlpha = 0.01f) + slideOutHorizontally(
                targetOffsetX = { it }
            )
        ) {
            val scope = rememberCoroutineScope()
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .noRippleClickable {
                        // 只有在引导期间才响应点击
                        if (isGuideActive) {
                            scope.launch {
                                showHand = false
                                pageState.animateScrollToPage(initialPageIndex)
                                IntySetting.setShowGuested()
                                onGuideCompleted()
                                isGuideActive = false
                            }
                        }
                    }
            ) {
                // 背景渐变框
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(top = 340.dp)
                        .size(210.dp, 40.dp)
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(
                                    Color.White.copy(0.7f),
                                    Color.White.copy(0.1f)
                                )
                            ),
                            shape = RoundedCornerShape(
                                topStart = 20.dp, bottomStart = 20.dp
                            )
                        )
                )

                // 手势图标
                Image(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(top = 340.dp, end = 92.dp)
                        .size(112.dp),
                    painter = painterResource(R.drawable.scroll_hand),
                    contentDescription = stringResource(R.string.content_desc_swipe_guide)
                )
            }
        }
    }
}
