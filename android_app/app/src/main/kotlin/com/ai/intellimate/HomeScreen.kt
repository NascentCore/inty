package com.ai.intellimate

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import android.app.Activity
import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil3.compose.AsyncImage
import com.ai.intellimate.agent.generate.CreateRoleActivity
import com.ai.intellimate.chat.ChatActivity
import com.ai.intellimate.login.LoginActivity
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.ExpiredVipDialog
import com.ai.intellimate.ui.components.ForceUpgradeDialog
import com.ai.intellimate.vip.VipCenterActivity
import com.ai.intellimate.chat.ChatPageContainer
import com.ai.intellimate.chat.ChatViewModel
import com.ai.intellimate.chat.viewmodel.ChatTabViewModel
import com.ai.intellimate.explore.ExplorePage
import com.ai.intellimate.explore.ExploreViewModel
import com.ai.intellimate.messages.ConversationsPage
import com.ai.intellimate.profile.ProfilePage

/** 主页面，包含五个tab */
@Composable
fun HomeScreen(
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    viewModelFactory: ViewModelProvider.Factory,
) {
    val selectedTab = mainViewModel.selectedTab.collectAsState()
    val context = LocalContext.current

    // 创建ExploreViewModel实例，用于ExploreTab
    val exploreViewModel: ExploreViewModel = viewModel()

    // 创建ChatTabViewModel实例，用于ChatTab
    val chatTabViewModel: ChatTabViewModel = viewModel()

    // 初始化Paging数据
    LaunchedEffect(Unit) {
        exploreViewModel.initializePagingData()
        chatTabViewModel.initializePagingData()
    }

    // 启动预加载数据监听
    LaunchedEffect(Unit) {
        exploreViewModel.startListeningPreloadUpdates()
        chatTabViewModel.startListeningPreloadUpdates()
    }

    // 跟踪HomeScreen页面访问
    // 使用 PageTrackingHelper 进行页面跟踪
    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView("HomeScreen", "MainActivity")
    }

    Scaffold(
        modifier = modifier
            .fillMaxSize()
            .background(HeartColor.primaryColor)
            .navigationBarsPadding(),
        containerColor = Color.Transparent,
        bottomBar = {
            AppBottomNavigationBar(
                modifier = Modifier,
                selectedTab = selectedTab.value.ordinal,
                onSelectTab = { tabIndex -> handleTabSelection(tabIndex, context, mainViewModel) },
            )
        },
    ) { innerPadding ->
        HomeContent(
            selectedTab = selectedTab.value,
            mainViewModel = mainViewModel,
            chatViewModel = chatViewModel,
            exploreViewModel = exploreViewModel,
            chatTabViewModel = chatTabViewModel,
            viewModelFactory = viewModelFactory,
            context = context,
            innerPadding = innerPadding,
        )

        ExpiredDialogLogic(mainViewModel)

        AppVersionLogic(mainViewModel)
    }
}

// App检查更新的逻辑，强制更新则弹窗
@Composable
private fun AppVersionLogic(mainViewModel: MainViewModel) {
    val uriHandler = LocalUriHandler.current
    val rsp by mainViewModel.needForceUpgrade.collectAsState()
    if (rsp?.force_update == true) {
        ForceUpgradeDialog(
            content = rsp?.message ?: stringResource(R.string.str_upgrade_content),
            onConfirm = {
                runCatching { rsp?.download_url?.let { url -> uriHandler.openUri(url) } }
            },
        )
    }
}

@Composable
private fun ExpiredDialogLogic(mainViewModel: MainViewModel) {
    // 感知vip订阅过期的提示弹窗
    var showExpiredDialog by remember { mutableStateOf(false) }
    val vipStatue by mainViewModel.vipStatusFlow.collectAsState()
    val vipPlan by mainViewModel.vipPlanFlow.collectAsState()
    LifecycleResumeEffect(mainViewModel) {
        if (!vipStatue.isSubscribed && vipStatue.everSubscribed) {
            // 未订阅状态，且曾经订阅过，表示已过期;如果app未曾提示过一次，则弹窗。有过提示记录，则不弹窗
            if (
                !IntySetting.hasTipsVipExpired() &&
                IntySetting.isLogin() &&
                !IntySetting.isGuestUser()
            ) {
                showExpiredDialog = true
            }
        }
        onPauseOrDispose {}
    }
    if (showExpiredDialog) {
        val data =
            ChatDialogData(
                R.drawable.img_unlimit_dialog_bg,
                stringResource(R.string.str_expired_vip_dialog_content),
                stringResource(R.string.subscribe),
            )
        val context = LocalContext.current
        ExpiredVipDialog(
            data,
            onCancel = { showExpiredDialog = false },
            onSure = {
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    // 判断如果之前订阅的档位还在，则继续原订阅。如果没有了，则跳转到订阅中心
                    val plan =
                        vipPlan.find { plan -> plan.googleProductId == vipStatue.previous_plan_id }
                            ?: vipPlan.firstOrNull()

                    val googleProductId = plan?.googleProductId
                    if (googleProductId != null) {
                        // 启动购买流程
                        if (context is Activity)
                            BillingRepository.launchBillingFlow(context, googleProductId)
                    } else {
                        // 跳转到订阅中心
                        VipCenterActivity.launch(context)
                    }
                } else {
                    // 如果未登录，要求先登录
                    LoginActivity.launch(context)
                }

                showExpiredDialog = false
            },
        )
        // 标记已经展示了tips的dialog
        IntySetting.setTipsVipExpired(true)
    }
}

/** 处理Tab选择逻辑 */
private fun handleTabSelection(tabIndex: Int, context: Context, mainViewModel: MainViewModel) {
    if (tabIndex == HomeTabIndex.Create.ordinal) {
        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
            CreateRoleActivity.launch(context)
        } else {
            LoginActivity.launch(context)
        }
        return
    }
    mainViewModel.selectTab(tabIndex)
}

/** 主页面内容 */
@Composable
private fun HomeContent(
    selectedTab: HomeTabIndex,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    exploreViewModel: ExploreViewModel,
    chatTabViewModel: ChatTabViewModel,
    viewModelFactory: ViewModelProvider.Factory,
    context: Context,
    innerPadding: PaddingValues,
) {
    when (selectedTab) {
        HomeTabIndex.Chat -> {
            ChatTabContent(
                mainViewModel = mainViewModel,
                chatTabViewModel = chatTabViewModel,
                viewModelFactory = viewModelFactory,
            )
        }

        HomeTabIndex.Conversation -> {
            ConversationsTabContent(chatViewModel = chatViewModel, context = context)
        }

        HomeTabIndex.Create -> {
            // Create tab is handled in handleTabSelection
        }

        HomeTabIndex.Explore -> {
            ExploreTabContent(
                exploreViewModel = exploreViewModel,
                context = context,
                innerPadding = innerPadding,
            )
        }

        HomeTabIndex.Profile -> {
            ProfileTabContent(mainViewModel = mainViewModel, context = context)
        }
    }
}

/** 聊天Tab内容 */
@Composable
private fun ChatTabContent(
    mainViewModel: MainViewModel,
    chatTabViewModel: ChatTabViewModel,
    viewModelFactory: ViewModelProvider.Factory,
) {
    val userProfile = mainViewModel.userProfile.collectAsState()
    val currentChatPageIndex = mainViewModel.currentChatPageIndex.collectAsState()

    ChatPageContainer(
        modifier = Modifier,
        viewModelFactory = viewModelFactory,
        chatTabViewModel = chatTabViewModel,
        userProfile = userProfile.value,
        currentPageIndex = currentChatPageIndex.value,
        onPageChanged = { index -> mainViewModel.updateCurrentChatPageIndex(index) },
    )
}

/** 会话Tab内容 */
@Composable
private fun ConversationsTabContent(chatViewModel: ChatViewModel, context: Context) {
    val conversations by chatViewModel.conversations.collectAsState()
    val isLoadingConversations by chatViewModel.isLoadingConversations.collectAsState()
    val isRefreshingConversations by chatViewModel.isRefreshingConversations.collectAsState()

    ConversationsPage(
        modifier = Modifier,
        conversations = conversations,
        onClickConversationItem = { conversation ->
            chatViewModel.setConversationReaded(conversation)
            // 从会话列表 跳转到聊天页面，
            ChatActivity.launch(context, conversation.convertToAgentInfo())
        },
        isLoadingConversations = isLoadingConversations,
        isRefreshingConversations = isRefreshingConversations,
        onLoadMoreConversations = { chatViewModel.loadMoreConversations() },
    )
}

/** 推荐Tab内容 */
@Composable
private fun ExploreTabContent(
    exploreViewModel: ExploreViewModel,
    context: Context,
    innerPadding: PaddingValues,
) {
    ExplorePage(
        modifier = Modifier,
        innerPadding = innerPadding,
        onClickAgent = { agent ->
            ChatActivity.launch(context, agent)
        },
        viewModel = exploreViewModel,
    )
}

/** 我的Tab内容 */
@Composable
private fun ProfileTabContent(mainViewModel: MainViewModel, context: Context) {
    val userProfile by mainViewModel.userProfile.collectAsStateWithLifecycle()
    val userCreatedAgents = mainViewModel.userCreatedAgents
    val isLoadingUserAgents = mainViewModel.isLoadingUserAgents.collectAsState()
    val isRefreshingUserAgents = mainViewModel.isRefreshingUserAgents.collectAsState()

    // 确保用户信息有效，避免崩溃
    val safeUserProfile =
        userProfile.let { profile ->
            if (profile.id.isEmpty()) {
                UserProfile(
                    id = "loading",
                    nickname = "Loading...",
                    avatar = null,
                    description = "UserInfo Loading...",
                )
            } else {
                profile
            }
        }
    LaunchedEffect(mainViewModel) {
        mainViewModel.updateUserInfoLocal()
    }
    // 确保更新用户信息，处理切换账号后的信息同步
    LifecycleResumeEffect(mainViewModel) {
        mainViewModel.getUserProfile()
        // 刷新订阅状态
        VipStatusHelper.refreshSubscriptionStatus()
        onPauseOrDispose {}
    }
    ProfilePage(
        modifier = Modifier,
        userProfile = safeUserProfile,
        agents = userCreatedAgents,
        isLoading = isLoadingUserAgents.value,
        isRefreshing = isRefreshingUserAgents.value,
        onClickAgent = { agent ->
            ChatActivity.launch(context, agent)
        },
        onEditAgent = { agent ->
            CreateRoleActivity.launch(context, agent)
        },
        onDeleteAgent = { agent ->
            mainViewModel.deleteAgent(
                agentId = agent.id,
                onSuccess = {
                    // 删除成功，列表会自动更新
                },
                onError = { _ ->
                    // 错误处理已在ViewModel中完成
                },
            )
        },
        onLoadMore = { mainViewModel.loadMoreUserCreatedAgents() },
    )
}

private data class TabInfo(val icon: Int, val iconSelected: Int, val label: Int)

private val MAIN_TAB_LIST =
    listOf(
        TabInfo(R.drawable.tab_icon_home, R.drawable.tab_icon_home_selected, R.string.tab_home),
        TabInfo(
            R.drawable.tab_icon_messages,
            R.drawable.tab_icon_messages_selected,
            R.string.tab_messages,
        ),
        TabInfo(
            R.drawable.tab_icon_create,
            R.drawable.tab_icon_create,
            R.string.tab_create,
        ), // Create tab 不需要文字标签
        TabInfo(
            R.drawable.tab_icon_explore,
            R.drawable.tab_icon_explore_selected,
            R.string.tab_explore,
        ),
        TabInfo(R.drawable.tab_icon_me, R.drawable.tab_icon_me_selected, R.string.tab_me),
    )

val BottomNavigationBarHeight = 64.dp

@Composable
private fun AppBottomNavigationBar(
    modifier: Modifier,
    selectedTab: Int,
    onSelectTab: (Int) -> Unit,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(HeartColor.primaryColor)
            .height(BottomNavigationBarHeight),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        MAIN_TAB_LIST.forEachIndexed { index, tab ->
            BottomNavigationBarItem(
                modifier =
                    Modifier
                        .fillMaxHeight()
                        .weight(1f)
                        .noRippleClickable { onSelectTab(index) },
                tabInfo = tab,
                selected = (index == selectedTab),
            )
        }
    }
}

val TabIconSize = 26.dp

@Composable
private fun BottomNavigationBarItem(modifier: Modifier, tabInfo: TabInfo, selected: Boolean) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Bottom,
    ) {
        AsyncImage(
            modifier = Modifier.size(TabIconSize),
            model = if (selected) tabInfo.iconSelected else tabInfo.icon,
            contentScale = ContentScale.Fit, // 保持图片宽高比不变
            alignment = Alignment.Center,
            contentDescription = null,
        )

        val spacerRatio = 0.05f
        val spacerHeight = TabIconSize.value * spacerRatio
        Spacer(
            modifier = Modifier.height(spacerHeight.dp)
        ) // Vertical spacing between icon and text

        val tabTextFontSizeRatio = 0.45f
        val tabTextFontSize = TabIconSize.value * tabTextFontSizeRatio
        Text(
            text = stringResource(tabInfo.label),
            fontSize = tabTextFontSize.sp,
            fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
            color = if (selected) Color(0xFF9C27B0) else Color.White, // 选中时使用紫色，未选中时使用白色
        )
    }
}

@Preview(showBackground = true)
@Composable
fun AppBottomNavigationBarPreview() {
    // Preview for the entire bottom navigation bar positioned in the middle
    Box(
        modifier =
            Modifier
                .fillMaxSize()
                .background(Color.Black), // Dark background to match the app theme
        contentAlignment = Alignment.Center,
    ) {
        AppBottomNavigationBar(
            modifier = Modifier,
            selectedTab = 0, // Home tab selected
            onSelectTab = { /* Preview doesn't need actual functionality */ },
        )
    }
}
