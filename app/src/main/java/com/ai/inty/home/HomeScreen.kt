package com.ai.inty.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.UserProfile
import com.ai.inty.chat.ChatPageContainer
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.viewmodels.ChatViewModel
import com.ai.inty.viewmodels.HomeTabIndex
import com.ai.inty.viewmodels.MainViewModel
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter

data class TabInfo(
    val normalImage: Int,
    val selectedImage: Int,
)

val MAIN_TAB_LIST = listOf(
    TabInfo(R.drawable.tab_chat, R.drawable.tab_chat_selected),
    TabInfo(R.drawable.tab_msg, R.drawable.tab_msg_selected),
    TabInfo(R.drawable.tab_add, R.drawable.tab_add),
    TabInfo(R.drawable.tab_suggest, R.drawable.tab_suggest_selected),
    TabInfo(R.drawable.tab_my, R.drawable.tab_my_selected),
)

/**
 * 主页面，包含五个tab
 */
@Composable
fun HomeScreen(
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    viewModelFactory: ViewModelProvider.Factory,
) {
    val selectedTab = mainViewModel.selectedTab.collectAsState()
    val selectedConversionsTab = mainViewModel.selectedConversionsTab.collectAsState()
    val agentList = mainViewModel.agentList
    val context = LocalContext.current

    Scaffold(
        modifier = modifier
            .fillMaxSize()
            .background(BackGround)
            .navigationBarsPadding(),
        containerColor = Color.Transparent,
        bottomBar = {
            HomeBottomBar(
                modifier = Modifier,
                selectedTab = selectedTab.value.ordinal,
                onSelectTab = { tabIndex ->
                    handleTabSelection(tabIndex, context, mainViewModel)
                }
            )
        }
    ) { _ ->
        HomeContent(
            selectedTab = selectedTab.value,
            selectedConversionsTab = selectedConversionsTab.value,
            mainViewModel = mainViewModel,
            chatViewModel = chatViewModel,
            viewModelFactory = viewModelFactory,
            context = context
        )
    }
}

/**
 * 处理Tab选择逻辑
 */
private fun handleTabSelection(
    tabIndex: Int,
    context: android.content.Context,
    mainViewModel: MainViewModel,
) {
    if (tabIndex == HomeTabIndex.Add.ordinal) {
        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
            TheRouter.build(Constant.ROUTE_CREATE_ROLE).navigation(context)
        } else {
            TheRouter.build(Constant.ROUTE_LOGIN).navigation(context)
        }
        return
    }
    mainViewModel.selectTab(tabIndex)
}

/**
 * 主页面内容
 */
@Composable
private fun HomeContent(
    selectedTab: HomeTabIndex,
    selectedConversionsTab: com.ai.inty.home.ConversionsPageTab,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    viewModelFactory: ViewModelProvider.Factory,
    context: android.content.Context,
) {
    when (selectedTab) {
        HomeTabIndex.Chat -> {
            ChatTabContent(
                mainViewModel = mainViewModel,
                viewModelFactory = viewModelFactory
            )
        }

        HomeTabIndex.Conversions -> {
            ConversionsTabContent(
                mainViewModel = mainViewModel,
                chatViewModel = chatViewModel,
                selectedConversionsTab = selectedConversionsTab,
                context = context
            )
        }

        HomeTabIndex.Add -> {
            // Add tab is handled in handleTabSelection
        }

        HomeTabIndex.Suggest -> {
            SuggestTabContent(
                mainViewModel = mainViewModel,
                context = context
            )
        }

        HomeTabIndex.My -> {
            MyTabContent(
                mainViewModel = mainViewModel,
                context = context
            )
        }
    }
}

/**
 * 聊天Tab内容
 */
@Composable
private fun ChatTabContent(
    mainViewModel: MainViewModel,
    viewModelFactory: ViewModelProvider.Factory,
) {
    val userProfile = mainViewModel.userProfile.collectAsState()
    val currentChatPageIndex = mainViewModel.currentChatPageIndex.collectAsState()

    ChatPageContainer(
        modifier = Modifier,
        viewModelFactory = viewModelFactory,
        agentList = mainViewModel.agentList,
        userProfile = userProfile.value,
        currentPageIndex = currentChatPageIndex.value,
        onPageChanged = { index ->
            mainViewModel.updateCurrentChatPageIndex(index)
        },
        onFollowAgent = { agentId ->
            handleFollowAgent(agentId, mainViewModel)
        }
    )
}

/**
 * 会话Tab内容
 */
@Composable
private fun ConversionsTabContent(
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    selectedConversionsTab: com.ai.inty.home.ConversionsPageTab,
    context: android.content.Context,
) {
    val conversions = chatViewModel.conversions
    val sysMsgs = mainViewModel.sysMsgs
    val followingAgents = mainViewModel.followingAgents

    ConversionsPage(
        modifier = Modifier,
        selectedTab = selectedConversionsTab,
        conversions = conversions,
        followingAgents = followingAgents,
        onSelectTab = {
            mainViewModel.onSelectConversionsTab(it)
        },
        onClickConversionItem = { conversation ->
            chatViewModel.setConversionReaded(conversation)
            TheRouter.build(Constant.ROUTE_CHAT)
                .withObject("agent_id", conversation.agentId)
                .navigation(context)
        },
        lastSysMsg = sysMsgs.firstOrNull(),
        onClickSysMsg = {
            IntySetting.setConversationReaded(
                Constant.SYS_NOTIFICATION_ID,
                sysMsgs.firstOrNull()?.content ?: ""
            )
            TheRouter.build(Constant.ROUTE_SYS_MSGS).navigation(context)
        },
        onClickFollowingAgent = { agent ->
            TheRouter.build(Constant.ROUTE_AGENT_INFO)
                .withObject("agent", agent)
                .navigation(context)
        },
        onUnfollowAgent = { agentId ->
            mainViewModel.unfollowAgent(agentId)
        }
    )
}

/**
 * 推荐Tab内容
 */
@Composable
private fun SuggestTabContent(
    mainViewModel: MainViewModel,
    context: android.content.Context,
) {
    val isLoading = mainViewModel.isLoading.collectAsState()

    RecommendPage(
        modifier = Modifier,
        agents = mainViewModel.agentList,
        isLoading = isLoading.value,
        onClickAgent = { agent ->
            TheRouter.build(Constant.ROUTE_CHAT)
                .withObject("agent", agent)
                .navigation(context)
        },
        onLoadMore = {
            mainViewModel.loadMoreAgents()
        },
        onRefresh = {
            mainViewModel.getAgents()
        }
    )
}

/**
 * 我的Tab内容
 */
@Composable
private fun MyTabContent(
    mainViewModel: MainViewModel,
    context: android.content.Context,
) {
    val userProfile = mainViewModel.userProfile.collectAsState()
    val userCreatedAgents = mainViewModel.userCreatedAgents
    val isLoadingUserAgents = mainViewModel.isLoadingUserAgents.collectAsState()

    // 确保用户信息有效，避免崩溃
    val safeUserProfile = userProfile.value.let { profile ->
        if (profile.id.isEmpty()) {
            UserProfile(
                id = "loading",
                nickname = "加载中...",
                avatar = null,
                description = "正在加载用户信息..."
            )
        } else {
            profile
        }
    }

    MyPage(
        modifier = Modifier,
        userProfile = safeUserProfile,
        agents = userCreatedAgents,
        isLoading = isLoadingUserAgents.value,
        onClickAgent = { agent ->
            TheRouter.build(Constant.ROUTE_CHAT)
                .withObject("agent", agent)
                .navigation(context)
        },
        onEditAgent = { agent ->
            TheRouter.build(Constant.ROUTE_CREATE_ROLE)
                .withObject("agent", agent)
                .navigation(context)
        },
        onDeleteAgent = { agent ->
            mainViewModel.deleteAgent(
                agentId = agent.id,
                onSuccess = {
                    // 删除成功，列表会自动更新
                },
                onError = { errorMessage ->
                    // 错误处理已在ViewModel中完成
                }
            )
        },
        onLoadMore = {
            mainViewModel.loadMoreUserCreatedAgents()
        }
    )
}

/**
 * 处理关注代理逻辑
 */
private fun handleFollowAgent(agentId: String, mainViewModel: MainViewModel) {
    val agent = mainViewModel.agentList.find { it.id == agentId }
    val isCurrentlyFollowed = agent?.isFollowed ?: false

    if (isCurrentlyFollowed) {
        mainViewModel.unfollowAgent(agentId)
    } else {
        mainViewModel.followAgent(agentId)
    }
}

/**
 * 底部导航栏
 */
@Composable
fun HomeBottomBar(
    modifier: Modifier,
    selectedTab: Int,
    onSelectTab: (Int) -> Unit,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(BackGround)
            .height(80.dp)
            .padding(bottom = 32.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        MAIN_TAB_LIST.forEachIndexed { index, tab ->
            BottomBarItem(
                modifier = Modifier
                    .fillMaxHeight()
                    .weight(1f)
                    .noRippleClickable {
                        onSelectTab(index)
                    },
                tabInfo = tab,
                selected = (index == selectedTab),
            )
        }
    }
}

/**
 * 底部导航栏项
 */
@Composable
fun BottomBarItem(
    modifier: Modifier,
    tabInfo: TabInfo,
    selected: Boolean,
) {
    Box(modifier = modifier) {
        IntyImage(
            modifier = Modifier
                .size(42.dp)
                .align(Alignment.Center),
            model = if (selected) tabInfo.selectedImage else tabInfo.normalImage
        )
    }
}

