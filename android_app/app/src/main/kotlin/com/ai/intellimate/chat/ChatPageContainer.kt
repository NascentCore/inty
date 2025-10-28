package com.ai.intellimate.chat

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
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
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import com.ai.intellimate.R
import com.ai.intellimate.audio.AudioManager
import com.ai.intellimate.chat.viewmodel.ChatTabViewModel
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** ChatPageContainer - 支持分页加载的聊天页面容器 使用Paging库实现分页加载更多agents，提供更流畅的滑动体验 */
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
    val agentList =
        remember(agentsPagingItems.itemCount) {
            val list = mutableListOf<AgentInfo>()
            try {
                for (i in 0 until agentsPagingItems.itemCount) {
                    agentsPagingItems[i]?.let { agent -> list.add(agent) }
                }
            } catch (e: IndexOutOfBoundsException) {
                LogUtils.w("ChatPageContainer - 构建agentList时索引越界: ${e.message}")
            } catch (e: Exception) {
                LogUtils.e("ChatPageContainer - 构建agentList时发生异常: ${e.message}")
            }
            list
        }

    // 如果 agentList 为空，显示加载状态而不是空白
    if (agentList.isEmpty()) {
        Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            // 显示加载指示器，而不是空白
            androidx.compose.material3.CircularProgressIndicator(
                color = androidx.compose.material3.MaterialTheme.colorScheme.primary
            )
        }
        return
    }

    // 防止初始页面索引越界
    val safeInitialPage =
        if (currentPageIndex >= 0 && currentPageIndex < agentList.size) {
            currentPageIndex
        } else {
            0 // 默认使用第一页
        }
    val pageState = rememberPagerState(initialPage = safeInitialPage) { agentList.size }
    val prefetchThreshold = 5 // 距离本业末尾数据还有5个时，触发静默加载下一页
    val scope = rememberCoroutineScope()

    // 新用户引导状态
    var hasShowGuest by remember { mutableStateOf(IntySetting.hasShowGuest()) }
    val shouldShowGuide =
        remember(agentList.size, hasShowGuest) { !hasShowGuest && agentList.size > 1 }

    // 监听页面变化
    LaunchedEffect(pageState.currentPage) {
        onPageChanged(pageState.currentPage)

        // 页面切换时停止当前播放的音频，避免播放错误agent的音频
        val currentAgent = agentList.getOrNull(pageState.currentPage)
        if (currentAgent != null) {
            try {
                val audioManager = AudioManager.getInstance(Utils.getApp(), scope)
                audioManager.stopAllPlayback()
            } catch (e: Exception) {
                LogUtils.e("ChatPageContainer - 停止音频播放失败: ${e.message}")
            }
            delay(100)
        }

        // 静默预取：当滑到倒数第5个左右时，触发下一页加载（无可见提示）
        val total = agentList.size
        if (total > 0) {
            val thresholdIndex = (total - prefetchThreshold).coerceAtLeast(0)
            val appendState = agentsPagingItems.loadState.append
            val refreshState = agentsPagingItems.loadState.refresh
            val notEnd =
                !(appendState is LoadState.NotLoading && appendState.endOfPaginationReached)
            val canPrefetch = refreshState is LoadState.NotLoading
            if (pageState.currentPage >= thresholdIndex && notEnd && canPrefetch) {
                // 修复：使用更安全的预取方式
                // 通过访问最后一个有效索引来触发Paging的append加载
                try {
                    val lastValidIndex = (agentsPagingItems.itemCount - 1).coerceAtLeast(0)
                    if (lastValidIndex >= 0 && lastValidIndex < agentsPagingItems.itemCount) {
                        // 访问最后一个有效索引，这会触发Paging库自动加载下一页
                        agentsPagingItems[lastValidIndex]
                    }
                } catch (e: IndexOutOfBoundsException) {
                    LogUtils.w("ChatPageContainer - 索引越界，跳过预取: ${e.message}")
                } catch (e: Exception) {
                    LogUtils.w("ChatPageContainer - 预取触发失败: ${e.message}")
                }
            }
        }
    }

    Box {
        HorizontalPager(
            modifier = modifier,
            state = pageState,
            userScrollEnabled = !shouldShowGuide, // 在引导期间禁用用户滑动
            beyondViewportPageCount = 3, // 左右预先处理个page个数
        ) { currentPage ->
            // 防止数组越界
            if (currentPage < 0 || currentPage >= agentList.size) {
                LogUtils.w(
                    "ChatPageContainer - HorizontalPager索引越界: currentPage=$currentPage, agentList.size=${agentList.size}"
                )
                // 如果索引无效，显示空页面或返回
                return@HorizontalPager
            }
            val agent = agentList.getOrNull(currentPage)
            if (agent == null) {
                LogUtils.w("ChatPageContainer - 获取agent失败: currentPage=$currentPage")
                return@HorizontalPager
            }
            val chatViewModel: ChatViewModel = viewModel(key = agent.id, factory = viewModelFactory)

            LaunchedEffect(key1 = agent.id, key2 = agent.isFollowed) {
                chatViewModel.setAgentInfo(agent)
                chatViewModel.setUserProfile(userProfile)
            }

            ChatPage(
                modifier = Modifier.fillMaxSize(),
                chatViewModel = chatViewModel,
                isCurrentPage = currentPage == pageState.currentPage,
            )
        }

        // 新用户聊天滑动引导
        NewUserGuide(
            pageState = pageState,
            shouldShowGuide = shouldShowGuide,
            onGuideCompleted = { hasShowGuest = true },
        )
    }
}

/** 新用户引导组件 */
@Composable
private fun NewUserGuide(
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
            enter =
                fadeIn() +
                    slideInHorizontally(
                        initialOffsetX = { fullWidth -> fullWidth / 6 } // 从屏幕右侧1/6处出现
                    ),
            exit = fadeOut(targetAlpha = 0.01f) + slideOutHorizontally(targetOffsetX = { it }),
        ) {
            val scope = rememberCoroutineScope()
            Box(
                modifier =
                    Modifier
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
                    modifier =
                        Modifier
                            .align(Alignment.TopEnd)
                            .padding(top = 340.dp)
                            .size(210.dp, 40.dp)
                            .background(
                                brush =
                                    Brush.horizontalGradient(
                                        colors =
                                            listOf(Color.White.copy(0.7f), Color.White.copy(0.1f))
                                    ),
                                shape = RoundedCornerShape(topStart = 20.dp, bottomStart = 20.dp),
                            )
                )

                // 手势图标
                Image(
                    modifier =
                        Modifier
                            .align(Alignment.TopEnd)
                            .padding(top = 340.dp, end = 92.dp)
                            .size(112.dp),
                    painter = painterResource(R.drawable.scroll_hand),
                    contentDescription = stringResource(R.string.content_desc_swipe_guide),
                )
            }
        }
    }
}
