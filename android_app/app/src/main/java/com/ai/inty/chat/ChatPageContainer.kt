package com.ai.inty.chat

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.MutableTransitionState
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
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.UserProfile
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun ChatPageContainer(
    modifier: Modifier,
    viewModelFactory: ViewModelProvider.Factory,
    agentList: List<AgentInfo>,
    userProfile: UserProfile,
    currentPageIndex: Int = 0,
    onPageChanged: (Int) -> Unit = {},
) {
    // 如果 agentList 为空，显示空状态
    if (agentList.isEmpty()) {
        Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            // 可以在这里显示加载中或空状态的UI
            // 暂时显示空白，等待数据加载
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
    val scope = rememberCoroutineScope()

    // 监听页面变化
    LaunchedEffect(pageState.currentPage) { onPageChanged(pageState.currentPage) }

    Box {
        HorizontalPager(modifier = modifier, state = pageState) { currentPage ->
            // 防止数组越界
            if (currentPage < 0 || currentPage >= agentList.size) {
                // 如果索引无效，显示空页面或返回
                return@HorizontalPager
            }
            val agent = agentList[currentPage]
            val chatViewModel: ChatViewModel = viewModel(key = agent.id, factory = viewModelFactory)

            LaunchedEffect(key1 = agent.id, key2 = agent.isFollowed) {
                chatViewModel.setAgentInfo(agent)
                chatViewModel.setUserProfile(userProfile)
            }

            ChatPage(modifier = Modifier.fillMaxSize(), chatViewModel = chatViewModel)
        }

        // 新用户聊天滑动引导
        NewUserGuide(agentList = agentList, pageState = pageState, scope = scope)
    }
}

/** 新用户引导组件 */
@Composable
private fun NewUserGuide(agentList: List<AgentInfo>, pageState: PagerState, scope: CoroutineScope) {
    var hasShowGuest by remember { mutableStateOf(IntySetting.hasShowGuest()) }

    if (!hasShowGuest && agentList.size > 1) {
        val density = LocalDensity.current
        val pageScrollPx = with(density) { 80.dp.toPx() }
        val showHand = MutableTransitionState(false)

        LaunchedEffect(Unit) {
            delay(3000)
            showHand.targetState = true
            pageState.animateScrollBy(pageScrollPx)
            IntySetting.setShowGuested()
            delay(1000)
            showHand.targetState = false
            pageState.animateScrollToPage(pageState.currentPage)
        }

        AnimatedVisibility(
            visibleState = showHand,
            enter =
                fadeIn() +
                    slideInHorizontally(
                        initialOffsetX = { fullWidth -> fullWidth / 6 } // 从屏幕右侧1/6处出现
                    ),
            exit = fadeOut(targetAlpha = 0.01f) + slideOutHorizontally(targetOffsetX = { it }),
        ) {
            Box(
                modifier =
                    Modifier.fillMaxSize().noRippleClickable {
                        scope.launch {
                            showHand.targetState = false
                            pageState.animateScrollToPage(pageState.currentPage)
                            hasShowGuest = true
                        }
                    }
            ) {
                // 背景渐变框
                Box(
                    modifier =
                        Modifier.align(Alignment.TopEnd)
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
                        Modifier.align(Alignment.TopEnd)
                            .padding(top = 340.dp, end = 92.dp)
                            .size(112.dp),
                    painter = painterResource(R.drawable.scroll_hand),
                    contentDescription = stringResource(R.string.content_desc_swipe_guide),
                )
            }
        }
    }
}
