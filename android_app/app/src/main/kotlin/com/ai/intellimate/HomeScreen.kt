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
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil3.compose.AsyncImage
import com.ai.intellimate.agent.generate.CreateRoleActivity
import com.ai.intellimate.chat.ChatActivity
import com.ai.intellimate.chat.ChatPageContainer
import com.ai.intellimate.chat.viewmodel.ChatTabViewModel
import com.ai.intellimate.explore.ExplorePage
import com.ai.intellimate.explore.ExploreViewModel
import com.ai.intellimate.messages.MessagesPage
import com.ai.intellimate.messages.MessagesViewModel
import com.ai.intellimate.profile.ProfilePage
import com.ai.intellimate.profile.ProfileViewModel
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.ExpiredVipDialog
import com.ai.intellimate.ui.components.ForceUpgradeDialog
import com.ai.intellimate.vip.VipCenterActivity

/** 主页面，包含五个tab */
@Composable
fun HomeScreen(
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
    viewModelFactory: ViewModelProvider.Factory,
) {
    val selectedTab = mainViewModel.selectedTab.collectAsState()

    // 页面跟踪
    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView("HomePage", "MainActivity")
    }

    // 创建共享的 CreateRoleActivity launcher，用于处理从 Create Tab 创建后的刷新
    // 当 CreateRoleActivity 返回成功时，如果当前在 Profile Tab，需要刷新列表
    var shouldRefreshProfile by remember { mutableStateOf(false) }
    val createRoleLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            // 标记需要刷新 Profile 列表
            shouldRefreshProfile = true
        }
    }

    Scaffold(
        modifier =
            modifier
                .fillMaxSize()
                .background(HeartColor.primaryColor)
                .navigationBarsPadding(),
        containerColor = Color.Transparent,
        bottomBar = {
            val context = LocalContext.current
            AppBottomNavigationBar(
                modifier = Modifier,
                selectedTab = selectedTab.value.ordinal,
                onSelectTab = { tabIndex ->
                    handleTabSelectionWithLauncher(
                        tabIndex,
                        context,
                        mainViewModel,
                        createRoleLauncher
                    )
                },
            )
        },
    ) { innerPadding ->
        HomeContent(
            selectedTab = selectedTab.value,
            mainViewModel = mainViewModel,
            viewModelFactory = viewModelFactory,
            innerPadding = innerPadding,
            shouldRefreshProfile = shouldRefreshProfile,
            onRefreshProfileHandled = { shouldRefreshProfile = false },
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
                IntySetting.getCurToken().isNotEmpty()
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
                // 检查是否已登录
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
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
                        VipCenterActivity.launch(context, VipCenterActivity.HOME_EXPIRED_DIALOG)
                    }
                }

                showExpiredDialog = false
            },
        )
        // 标记已经展示了tips的dialog
        IntySetting.setTipsVipExpired(true)
    }
}

/** 处理Tab选择逻辑（带 launcher） */
private fun handleTabSelectionWithLauncher(
    tabIndex: Int,
    context: Context,
    mainViewModel: MainViewModel,
    createRoleLauncher: ActivityResultLauncher<Intent>,
) {
    if (tabIndex == HomeTabIndex.Create.ordinal) {
        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
            // 使用 CreateRoleActivity 提供的方法获取 Intent
            val intent = CreateRoleActivity.getIntent(context, null)
            createRoleLauncher.launch(intent)
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
    viewModelFactory: ViewModelProvider.Factory,
    innerPadding: PaddingValues,
    shouldRefreshProfile: Boolean,
    onRefreshProfileHandled: () -> Unit,
) {
    when (selectedTab) {
        HomeTabIndex.Chat -> {
            ChatTabContent(
                mainViewModel = mainViewModel,
                viewModelFactory = viewModelFactory,
            )
        }

        HomeTabIndex.Conversation -> {
            ConversationsTabContent()
        }

        HomeTabIndex.Create -> {
            // Create tab 在 handleTabSelection 中处理，不显示内容
        }

        HomeTabIndex.Explore -> {
            ExploreTabContent(innerPadding = innerPadding)
        }

        HomeTabIndex.Profile -> {
            ProfileTabContent(
                onShowSettings = { mainViewModel.showSettings() },
                shouldRefreshProfile = shouldRefreshProfile,
                onRefreshProfileHandled = onRefreshProfileHandled,
            )
        }
    }
}

/** 聊天Tab内容 */
@Composable
private fun ChatTabContent(
    mainViewModel: MainViewModel,
    viewModelFactory: ViewModelProvider.Factory,
) {
    val chatTabViewModel: ChatTabViewModel = viewModel()
    val userProfile = mainViewModel.userProfile.collectAsState()
    val currentChatPageIndex = mainViewModel.currentChatPageIndex.collectAsState()

    // 初始化 ChatTab 数据
    LaunchedEffect(Unit) {
        chatTabViewModel.initializePagingData()
        chatTabViewModel.startListeningPreloadUpdates()
    }

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
private fun ConversationsTabContent() {
    val context = LocalContext.current
    val messagesViewModel: MessagesViewModel = viewModel()

    LaunchedEffect(Unit) {
        messagesViewModel.getConversations()
    }

    MessagesPage(
        modifier = Modifier,
        viewModel = messagesViewModel,
        onClickConversationItem = { conversation ->
            messagesViewModel.setConversationReaded(conversation)
            ChatActivity.launch(
                context,
                conversation.convertToAgentInfo(),
                pageSource = ChatActivity.MESSAGES_TAB
            )
        },
        pageTrackingContext = "MainActivity",
    )
}

/** 推荐Tab内容 */
@Composable
private fun ExploreTabContent(innerPadding: PaddingValues) {
    val context = LocalContext.current
    val exploreViewModel: ExploreViewModel = viewModel()

    // 初始化 ExploreTab 数据
    LaunchedEffect(Unit) {
        exploreViewModel.initializePagingData()
        exploreViewModel.startListeningPreloadUpdates()
        exploreViewModel.startListeningUserAccountReady()
    }

    ExplorePage(
        modifier = Modifier,
        innerPadding = innerPadding,
        onClickAgent = { agent ->
            ChatActivity.launch(
                context,
                agent,
                pageSource = ChatActivity.EXPLORE_TAB
            )
        },
        viewModel = exploreViewModel,
    )
}

/** 我的Tab内容 */
@Composable
private fun ProfileTabContent(
    onShowSettings: () -> Unit,
    shouldRefreshProfile: Boolean,
    onRefreshProfileHandled: () -> Unit,
) {
    val context = LocalContext.current
    val profileViewModel: ProfileViewModel = viewModel()
    val uiState by profileViewModel.uiState.collectAsStateWithLifecycle()

    // 确保用户信息有效，避免崩溃
    val safeUserProfile = if (uiState.userProfile.id.isEmpty()) {
        UserProfile(
            id = "loading",
            nickname = "Loading...",
            avatar = null,
            description = "UserInfo Loading...",
        )
    } else {
        uiState.userProfile
    }

    // 创建用于编辑的 launcher（独立于 Create Tab 的 launcher）
    val editAgentLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        // 编辑成功后刷新列表
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            profileViewModel.refreshCreatedAgents()
        }
    }

    // 初始化数据：优先从缓存加载，避免闪现
    var hasInitialized by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        if (!hasInitialized) {
            hasInitialized = true
            profileViewModel.updateUserInfoLocal()
            // 优先从缓存加载，避免闪现
            profileViewModel.loadUserCreatedAgentsFromCache()
            profileViewModel.trackPageView("MainPage")
        }
    }

    // 监听从 Create Tab 创建成功后需要刷新的标志
    LaunchedEffect(shouldRefreshProfile) {
        if (shouldRefreshProfile) {
            profileViewModel.refreshCreatedAgents()
            onRefreshProfileHandled()
        }
    }

    // 生命周期管理：页面恢复时刷新用户信息，但不频繁刷新列表
    LifecycleResumeEffect(profileViewModel) {
        profileViewModel.loadUserProfile()
        VipStatusHelper.refreshSubscriptionStatus()
        // 不再频繁刷新列表，只在首次加载或从 CreateRoleActivity 返回时刷新
        onPauseOrDispose {}
    }

    ProfilePage(
        modifier = Modifier,
        userProfile = safeUserProfile,
        agents = uiState.userCreatedAgents,
        isLoading = uiState.isLoading,
        onClickAgent = { agent ->
            ChatActivity.launch(
                context,
                agent,
                pageSource = ChatActivity.PROFILE_TAB
            )
        },
        onEditAgent = { agent ->
            // 使用 CreateRoleActivity 提供的方法获取 Intent，并监听返回结果
            val intent = CreateRoleActivity.getIntent(context, agent)
            editAgentLauncher.launch(intent)
        },
        onDeleteAgent = { agent ->
            profileViewModel.deleteAgent(
                agentId = agent.id,
                onSuccess = { /* 删除成功，列表会自动更新 */ },
                onError = { /* 错误处理已在ViewModel中完成 */ },
            )
        },
        onLoadMore = { profileViewModel.loadMoreUserCreatedAgents() },
        onShowSettings = onShowSettings,
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
        modifier =
            modifier
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
