package com.ai.inty.home

import android.app.Activity
import android.content.Context
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.UserProfile
import com.ai.inty.billing.BillingRepository
import com.ai.inty.billing.VipStatusHelper
import com.ai.inty.chat.ChatPageContainer
import com.ai.inty.ui.ChatDialogData
import com.ai.inty.ui.ExpiredVipDialog
import com.ai.inty.ui.components.ForceUpgradeDialog
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.viewmodels.ChatViewModel
import com.ai.inty.viewmodels.HomeTabIndex
import com.ai.inty.viewmodels.MainViewModel
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter

private data class TabInfo(
    val normalImage: Int,
    val selectedImage: Int,
)

private val MAIN_TAB_LIST = listOf(
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
    val selectedConversationsTab = mainViewModel.selectedConversationsTab.collectAsState()
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
            selectedConversationsTab = selectedConversationsTab.value,
            mainViewModel = mainViewModel,
            chatViewModel = chatViewModel,
            viewModelFactory = viewModelFactory,
            context = context
        )

        ExpiredDialogLogic(mainViewModel)

        AppVersionLogic(mainViewModel)
    }
}

//App检查更新的逻辑，强制更新则弹窗
@Composable
private fun AppVersionLogic(mainViewModel: MainViewModel) {
    val uriHandler = LocalUriHandler.current
    val rsp by mainViewModel.needForceUpgrade.collectAsState()
    if (rsp?.force_update == true) {
        ForceUpgradeDialog(
            content = rsp?.message ?: stringResource(R.string.str_upgrade_content),
            onConfirm = {
                runCatching {
                    rsp?.download_url?.let { url ->
                        uriHandler.openUri(url)
                    }
                }
            }
        )
    }
}


@Composable
private fun ExpiredDialogLogic(mainViewModel: MainViewModel) {
    //感知vip订阅过期的提示弹窗
    var showExpiredDialog by remember { mutableStateOf(false) }
    val vipStatue by mainViewModel.vipStatusFlow.collectAsState()
    val vipPlan by mainViewModel.vipPlanFlow.collectAsState()
    LifecycleResumeEffect(mainViewModel) {
        if (!vipStatue.isSubscribed && vipStatue.everSubscribed) {
            //未订阅状态，且曾经订阅过，表示已过期;如果app未曾提示过一次，则弹窗。有过提示记录，则不弹窗
            if (!IntySetting.hasTipsVipExpired() && IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                showExpiredDialog = true
            }
        }
        onPauseOrDispose {

        }
    }
    if (showExpiredDialog) {
        val data = ChatDialogData(
            R.drawable.img_unlimit_dialog_bg,
            stringResource(R.string.str_expired_vip_dialog_content),
            stringResource(R.string.subscribe)
        )
        val context = LocalContext.current
        ExpiredVipDialog(
            data,
            onCancel = { showExpiredDialog = false },
            onSure = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    //判断如果之前订阅的档位还在，则继续原订阅。如果没有了，则跳转到订阅中心
                    val plan =
                        vipPlan.find { plan -> plan.googleProductId == vipStatue.previous_plan_id }
                            ?: vipPlan.firstOrNull()

                    val googleProductId = plan?.googleProductId
                    if (googleProductId != null) {
                        // 启动购买流程
                        if (context is Activity)
                            BillingRepository.launchBillingFlow(context, googleProductId)
                    } else {
                        //跳转到订阅中心
                        TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation()
                    }
                } else {
                    //如果未登录，要求先登录
                    TheRouter.build(Constant.ROUTE_LOGIN)
                        .navigation(context)
                }

                showExpiredDialog = false
            })
        //标记已经展示了tips的dialog
        IntySetting.setTipsVipExpired(true)
    }
}

/**
 * 处理Tab选择逻辑
 */
private fun handleTabSelection(
    tabIndex: Int,
    context: Context,
    mainViewModel: MainViewModel,
) {
    if (tabIndex == HomeTabIndex.Create.ordinal) {
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
    selectedConversationsTab: ConversationsPageTab,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    viewModelFactory: ViewModelProvider.Factory,
    context: Context,
) {
    when (selectedTab) {
        HomeTabIndex.Chat -> {
            ChatTabContent(
                mainViewModel = mainViewModel,
                viewModelFactory = viewModelFactory
            )
        }

        HomeTabIndex.Conversation -> {
            ConversationsTabContent(
                mainViewModel = mainViewModel,
                chatViewModel = chatViewModel,
                selectedConversationsTab = selectedConversationsTab,
                context = context
            )
        }

        HomeTabIndex.Create -> {
            // Create tab is handled in handleTabSelection
        }

        HomeTabIndex.Explore -> {
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
private fun ConversationsTabContent(
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    selectedConversationsTab: ConversationsPageTab,
    context: Context,
) {
    val conversations by chatViewModel.conversations.collectAsState()
    val sysMsgs = mainViewModel.sysMsgs
    val followingAgents = mainViewModel.followingAgents
    val isLoadingConversations by chatViewModel.isLoadingConversations.collectAsState()
    val isLoadingFollowingAgents by mainViewModel.isLoadingFollowingAgents.collectAsState()

    ConversationsPage(
        modifier = Modifier,
        selectedTab = selectedConversationsTab,
        conversations = conversations,
        followingAgents = followingAgents,
        lastSysMsg = sysMsgs.firstOrNull(),
        onSelectTab = {
            mainViewModel.onSelectConversationsTab(it)
        },
        onClickConversationItem = { conversation ->
            chatViewModel.setConversationReaded(conversation)
            TheRouter.build(Constant.ROUTE_CHAT)
                .withObject("agent_id", conversation.agentId)
                .navigation(context)
        },
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
        },
        isLoadingConversations = isLoadingConversations,
        isLoadingFollowingAgents = isLoadingFollowingAgents,
        onLoadMoreConversations = {
            chatViewModel.loadMoreConversations()
        },
        onLoadMoreFollowingAgents = {
            mainViewModel.loadMoreFollowingAgents()
        }
    )
}

/**
 * 推荐Tab内容
 */
@Composable
private fun SuggestTabContent(
    mainViewModel: MainViewModel,
    context: Context,
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
            mainViewModel.refreshAgents()
        }
    )
}

/**
 * 我的Tab内容
 */
@Composable
private fun MyTabContent(
    mainViewModel: MainViewModel,
    context: Context,
) {
    val userProfile = mainViewModel.userProfile.collectAsState()
    val userCreatedAgents = mainViewModel.userCreatedAgents
    val isLoadingUserAgents = mainViewModel.isLoadingUserAgents.collectAsState()

    // 确保用户信息有效，避免崩溃
    val safeUserProfile = userProfile.value.let { profile ->
        if (profile.id.isEmpty()) {
            UserProfile(
                id = "loading",
                nickname = "Loading...",
                avatar = null,
                description = "UserInfo Loading..."
            )
        } else {
            profile
        }
    }
    //确保更新用户信息，处理切换账号后的信息同步
    LifecycleResumeEffect(mainViewModel) {
        mainViewModel.getUserProfile()
        //刷新订阅状态
        VipStatusHelper.refreshSubscriptionStatus()
        onPauseOrDispose {

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
private fun HomeBottomBar(
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
private fun BottomBarItem(
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
