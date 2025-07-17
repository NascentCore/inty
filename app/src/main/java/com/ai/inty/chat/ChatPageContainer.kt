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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.UserProfile
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.storage.IntySetting
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
    onFollowAgent: ((String) -> Unit)? = null,
) {
    val pageState = rememberPagerState(
        initialPage = currentPageIndex
    ) {
        agentList.size
    }
    val scope = rememberCoroutineScope()
    
    // 监听页面变化
    LaunchedEffect(pageState.currentPage) {
        onPageChanged(pageState.currentPage)
    }

    Box {
        HorizontalPager(
            modifier = modifier,
            state = pageState,
        ) { currentPage ->

            val agent = agentList.get(currentPage)

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
            	onFollowAgent = onFollowAgent,
            )
        }

        //新用户 聊天滑动引导
        var hasShowGuest by remember {
            mutableStateOf(IntySetting.hasShowGuest())
        }
        if ( !hasShowGuest && (agentList.size > 1) ) {

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
                enter = fadeIn() + slideInHorizontally(
                    initialOffsetX = { fullWidth ->
                        fullWidth
                    }
                ),
                exit = fadeOut(targetAlpha = 0.01f) + slideOutHorizontally(
                    targetOffsetX = { it }
                )
            ) {
                Box(modifier = Modifier
                    .fillMaxSize()
                    .noRippleClickable {
                        scope.launch {
                            showHand.targetState = false
                            pageState.animateScrollToPage(pageState.currentPage)
                            hasShowGuest = true
                        }
                    }) {
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
                    ) {}
                    Image(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(top = 340.dp, end = 92.dp)
                            .size(112.dp),
                        painter = painterResource(R.drawable.scroll_hand),
                        contentDescription = ""
                    )
                }
            }
        }
    }
}