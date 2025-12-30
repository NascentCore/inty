package com.ai.intellimate

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.HeartBottomAppBar
import ai.sxwl.android.design.ui.HeartBottomTabItem
import ai.sxwl.android.firebase.FirebaseManager
import android.app.Activity
import android.content.Context
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.agent.report.ReportActivity
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
import com.ai.intellimate.ui.FeedbackRequestDialog
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.UpgradeDialog
import com.ai.intellimate.xb.helper.AgentStore
import com.ai.intellimate.xb.navigation.Routes
import com.inty.api.models.api.v1.version.VersionCheckResponse
import java.util.concurrent.TimeUnit

/** 主页面，包含五个tab */
@Composable
fun HomeScreen(
    navController: NavController,
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
    viewModelFactory: ViewModelProvider.Factory,
) {
    val selectedTab = mainViewModel.selectedTab.collectAsState()
    val messagesTabHasPush by mainViewModel.messagesTabHasPush.collectAsState()
    val appUpdateTipsRedDot by mainViewModel.appUpdateTipsRedDot.collectAsState()

    // 页面跟踪，包含当前和默认首页 tab（只在首次加载时上报）
    LaunchedEffect(Unit) {
        // 获取默认首页 tab
        val defaultTabIndex =
            try {
                FirebaseManager.getRemoteConfigLong(
                    FirebaseManager.RemoteConfigKeys.HOME_PAGE_DEFAULT_TAB_INDEX
                )
                    .toInt()
            } catch (_: Exception) {
                0 // 默认值：Chat tab
            }
        val defaultTabName =
            when (defaultTabIndex) {
                0 -> "chat"
                3 -> "explore"
                else -> "other"
            }

        val currentTabName =
            when (selectedTab.value) {
                HomeTabIndex.Chat -> "chat"
                HomeTabIndex.Messages -> "messages"
                HomeTabIndex.Create -> "create"
                HomeTabIndex.Explore -> "explore"
                HomeTabIndex.Profile -> "profile"
            }

        PageTrackingHelper.trackPageView(
            "HomePage",
            "MainActivity",
            mapOf("current_tab" to currentTabName, "default_home_tab" to defaultTabName),
        )
    }

    // 创建共享的 CreateRoleActivity launcher，用于处理从 Create Tab 创建后的刷新
    // 当 CreateRoleActivity 返回成功时，如果当前在 Profile Tab，需要刷新列表
    var shouldRefreshProfile by remember { mutableStateOf(false) }
    val createRoleLauncher =
        rememberLauncherForActivityResult(
            contract = ActivityResultContracts.StartActivityForResult()
        ) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                // 标记需要刷新 Profile 列表，并切换回 “Me” 页面
                shouldRefreshProfile = true
                mainViewModel.selectTab(HomeTabIndex.Profile.ordinal)
            }
        }

    // 处理从CreateRoleScreen 页面返回的数据
    val currentEntry = navController.currentBackStackEntry
    val savedStateHandle = currentEntry?.savedStateHandle
    val result = savedStateHandle?.getLiveData<Int>("createBackCode")
    LaunchedEffect(result?.value) {
        result?.value?.let {
            if (result.value == Activity.RESULT_OK) {
                // 标记需要刷新 Profile 列表，并切换回 “Me” 页面
                shouldRefreshProfile = true
                mainViewModel.selectTab(HomeTabIndex.Profile.ordinal)
            }
        }
    }

    // 双击检测：跟踪最后点击的tab和时间
    var lastTabClickTime by remember { mutableLongStateOf(0L) }
    var lastTabIndex by remember { mutableIntStateOf(-1) }
    val doubleTapTimeoutMs = 300L // 双击检测时间窗口（毫秒）

    val bottomBarItems =
        remember(messagesTabHasPush, appUpdateTipsRedDot) {
            defaultTabItems.map { tab ->
                when (tab.index) {
                    HomeTabIndex.Messages.ordinal -> {
                        tab.copy(hasRedDot = messagesTabHasPush)
                    }

                    HomeTabIndex.Profile.ordinal -> {
                        tab.copy(hasRedDot = appUpdateTipsRedDot)
                    }

                    else -> {
                        tab
                    }
                }
            }
        }

    LaunchedEffect(selectedTab.value) {
        when (selectedTab.value) {
            HomeTabIndex.Messages -> {
                mainViewModel.clearMessagesTabPush()
            }

            HomeTabIndex.Profile -> {
                // 当前 app 运行期间不会改变是否有新版的提示，所以不需要清除
                mainViewModel.clearAppUpdateTipsRedDot()
            }

            else -> {}
        }
    }

    Scaffold(
        modifier = modifier
            .fillMaxSize()
            .background(HeartColor.primaryColor),
        containerColor = Color.Transparent,
        bottomBar = {
            val context = LocalContext.current
            HeartBottomAppBar(
                modifier = Modifier,
                selectedTab = selectedTab.value.ordinal,
                tabItems = bottomBarItems,
                onTabSelected = { tabIndex ->
                    val currentTime = System.currentTimeMillis()
                    val exploreTabIndex = HomeTabIndex.Explore.ordinal

                    // 检测双击：如果点击的是Explore tab，且与上次点击相同，且在时间窗口内
                    if (
                        tabIndex == exploreTabIndex &&
                        tabIndex == lastTabIndex &&
                        currentTime - lastTabClickTime < doubleTapTimeoutMs
                    ) {
                        // 双击Explore tab，触发重置
                        if (selectedTab.value == HomeTabIndex.Explore) {
                            mainViewModel.triggerExploreReset()
                        }
                        // 重置计时器，避免连续触发
                        lastTabClickTime = 0
                        lastTabIndex = -1
                    } else {
                        // 正常点击，更新记录
                        lastTabClickTime = currentTime
                        lastTabIndex = tabIndex
                        handleTabSelectionWithLauncher(
                            navController,
                            tabIndex,
                            context,
                            mainViewModel,
                            createRoleLauncher,
                        )
                    }
                },
                iconSize = UiConfigs.BottomBar.TabIconSize,
                textSize = (UiConfigs.BottomBar.TabIconSize.value * 0.45f).sp,
                height = UiConfigs.BottomBar.Height,
                labelSpacing = UiConfigs.BottomBar.TabIconLabelSpacing,
                bottomSpace = UiConfigs.BottomBar.BottomSpacing,
            )
        },
    ) { innerPadding ->
        HomeContent(
            navController,
            selectedTab = selectedTab.value,
            mainViewModel = mainViewModel,
            viewModelFactory = viewModelFactory,
            innerPadding = innerPadding,
            shouldRefreshProfile = shouldRefreshProfile,
            onRefreshProfileHandled = { shouldRefreshProfile = false },
        )

        ExpiredDialogLogic(navController, mainViewModel)
        AppVersionLogic(mainViewModel)
        FeedbackRequestDialogLogic(mainViewModel)
    }
}

// App检查更新的逻辑，强制更新则弹窗
@Composable
private fun AppVersionLogic(mainViewModel: MainViewModel) {
    val rsp by mainViewModel.needForceUpgrade.collectAsState(null)

    // 使用稳定的 key，避免 rsp 变化时重置状态；因为 rsp 会从 null 被赋值
    var shouldShowUpgradeDialog by remember { mutableStateOf(false) }

    // 只在首次收到非 null 的 rsp 时显示对话框
    LaunchedEffect(rsp) {
        if (rsp != null && !shouldShowUpgradeDialog) {
            shouldShowUpgradeDialog = true
        }
    }

    val isForced = rsp?.reminder_action == VersionCheckResponse.Data.ReminderAction.BLOCK_ACCESS
    val title =
        if (isForced) {
            stringResource(id = R.string.str_force_upgrade)
        } else {
            stringResource(id = R.string.str_suggest_upgrade)
        }
    val content = stringResource(id = R.string.str_upgrade_content)

    if (shouldShowUpgradeDialog && rsp != null) {
        UpgradeDialog(title, content, { shouldShowUpgradeDialog = false }, isForced = isForced)
    }
}

private val RESUB_REMINDER_CYCLE_SECONDS = TimeUnit.DAYS.toSeconds(1)
private val MAX_RESUB_REMINDER_CYCLE_SECONDS = TimeUnit.DAYS.toSeconds(32)
private val MAX_RESUB_REMINDER_MULTIPLIER =
    (MAX_RESUB_REMINDER_CYCLE_SECONDS / RESUB_REMINDER_CYCLE_SECONDS).toInt()

@Composable
private fun ExpiredDialogLogic(navController: NavController, mainViewModel: MainViewModel) {
    // 感知vip订阅过期的提示弹窗
    var showExpiredDialog by remember { mutableStateOf(false) }
    val vipStatue by mainViewModel.vipStatusFlow.collectAsState()
    val vipPlan by mainViewModel.vipPlanFlow.collectAsState()
    LifecycleResumeEffect(mainViewModel) {
        if (!vipStatue.isSubscribed && vipStatue.everSubscribed) {
            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                val nowSeconds = System.currentTimeMillis() / 1000
                val lastShowTime = IntySetting.getLastResubReminderDialogShowTime()
                val showCount = IntySetting.getResubReminderDialogShowCount()
                val shouldShowReminder =
                    shouldShowResubReminderDialog(nowSeconds, lastShowTime, showCount)
                if (shouldShowReminder) {
                    IntySetting.setLastResubReminderDialogShowTime(nowSeconds)
                    IntySetting.setResubReminderDialogShowCount(showCount + 1)
                    showExpiredDialog = true
                }
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
                        navController.navigate(Routes.Me.VipCenter)
                        //                        VipCenterActivity.launch(context,
                        // VipCenterActivity.HOME_EXPIRED_DIALOG)
                    }
                }

                showExpiredDialog = false
            },
        )
    }
}

@Composable
private fun FeedbackRequestDialogLogic(mainViewModel: MainViewModel) {
    val showDialog by mainViewModel.showFeedbackRequestDialog.collectAsState()
    val context = LocalContext.current

    if (showDialog) {
        FeedbackRequestDialog(
            onCancel = { mainViewModel.hideFeedbackRequestDialog() },
            onSendSuggestions = {
                mainViewModel.hideFeedbackRequestDialog()
                ReportActivity.launchFeedback(context)
            },
        )
    }
}

private fun shouldShowResubReminderDialog(
    nowSeconds: Long,
    lastShowTimeSeconds: Long,
    showCount: Int,
): Boolean {
    if (lastShowTimeSeconds == 0L) return true
    val delaySeconds = calculateResubReminderDelaySeconds(showCount)
    return nowSeconds - lastShowTimeSeconds >= delaySeconds
}

private fun calculateResubReminderDelaySeconds(showCount: Int): Long {
    val safeCount = showCount.coerceAtMost(30)
    val multiplier = (1 shl safeCount).coerceAtMost(MAX_RESUB_REMINDER_MULTIPLIER)
    return RESUB_REMINDER_CYCLE_SECONDS * multiplier
}

/** 处理Tab选择逻辑（带 launcher） */
private fun handleTabSelectionWithLauncher(
    navController: NavController,
    tabIndex: Int,
    context: Context,
    mainViewModel: MainViewModel,
    createRoleLauncher: ActivityResultLauncher<Intent>,
) {
    if (tabIndex == HomeTabIndex.Create.ordinal) {
        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
            // 使用 CreateRoleActivity 提供的方法获取 Intent
            //            val intent = CreateRoleActivity.getIntent(context, null)
            //            createRoleLauncher.launch(intent)
            navController.navigate(Routes.Creat.CreateRole)
        }
        return
    }
    mainViewModel.selectTab(tabIndex)
}

/** 主页面内容 */
@Composable
private fun HomeContent(
    navController: NavController,
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
                navController,
                mainViewModel = mainViewModel,
                viewModelFactory = viewModelFactory,
            )
        }

        HomeTabIndex.Messages -> {
            MessagesTabContent(navController, mainViewModel)
        }

        HomeTabIndex.Create -> {
            // Create tab 在 handleTabSelection 中处理，不显示内容
        }

        HomeTabIndex.Explore -> {
            ExploreTabContent(
                navController,
                innerPadding = innerPadding,
                mainViewModel = mainViewModel,
            )
        }

        HomeTabIndex.Profile -> {
            val appUpdateTips by mainViewModel.appUpdateTips.collectAsState()
            ProfileTabContent(
                navController,
                shouldRefreshProfile = shouldRefreshProfile,
                onRefreshProfileHandled = onRefreshProfileHandled,
                appUpdateTips = appUpdateTips,
            )
        }
    }
}

/** 聊天Tab内容 */
@Composable
private fun ChatTabContent(
    navController: NavController,
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
        navController,
        modifier = Modifier,
        viewModelFactory = viewModelFactory,
        chatTabViewModel = chatTabViewModel,
        userProfile = userProfile.value,
        currentPageIndex = currentChatPageIndex.value,
        onPageChanged = { index -> mainViewModel.updateCurrentChatPageIndex(index) },
    )
}

/** 会话列表Tab内容 */
@Composable
private fun MessagesTabContent(navController: NavController, mainViewModel: MainViewModel) {
    val messagesViewModel: MessagesViewModel = viewModel()

    LaunchedEffect(Unit) { messagesViewModel.getConversations() }

    MessagesPage(
        modifier = Modifier,
        viewModel = messagesViewModel,
        onClickConversationItem = { conversation ->
            AgentStore.addAgent(conversation.convertToAgentInfo())
            navController.navigate(
                Routes.Chat.chatPage(
                    conversation.convertToAgentInfo().id,
                    false,
                    isDeleted = conversation.isDeleted,
                )
            )
        },
        onClickFavoriteAgent = { agent ->
            AgentStore.addAgent(agent)
            navController.navigate(Routes.Chat.chatPage(agent.id, false))
        },
        onNavigateToExplore = { mainViewModel.selectTab(HomeTabIndex.Explore.ordinal) },
        pageTrackingContext = "MainActivity",
    )
}

/** 推荐Tab内容 */
@Composable
private fun ExploreTabContent(
    navController: NavController,
    innerPadding: PaddingValues,
    mainViewModel: MainViewModel,
) {
    val context = LocalContext.current
    val exploreViewModel: ExploreViewModel = viewModel()
    val exploreResetSignal by mainViewModel.exploreResetSignal.collectAsState()

    // 初始化 ExploreTab 数据
    LaunchedEffect(Unit) {
        exploreViewModel.initializePagingData()
        exploreViewModel.startListeningPreloadUpdates()
        exploreViewModel.startListeningUserAccountReady()
    }

    ExplorePage(
        navController,
        modifier = Modifier,
        innerPadding = innerPadding,
        onClickAgent = { agent ->
            AgentStore.addAgent(agent)
            navController.navigate(
                Routes.Chat.chatPage(agent.id, false, shouldAutoFocusInput = false)
            )
        },
        viewModel = exploreViewModel,
        externalResetSignal = exploreResetSignal,
    )
}

/** 我的Tab内容 */
@Composable
private fun ProfileTabContent(
    navController: NavController,
    shouldRefreshProfile: Boolean,
    onRefreshProfileHandled: () -> Unit,
    appUpdateTips: Boolean,
) {
    val context = LocalContext.current
    val profileViewModel: ProfileViewModel = viewModel()
    val uiState by profileViewModel.uiState.collectAsStateWithLifecycle()

    // 确保用户信息有效，避免崩溃
    val safeUserProfile =
        if (uiState.userProfile.id.isEmpty()) {
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
    //    val editAgentLauncher =
    //        rememberLauncherForActivityResult(
    //            contract = ActivityResultContracts.StartActivityForResult()
    //        ) { result ->
    //            // 编辑成功后刷新列表
    //            if (result.resultCode == Activity.RESULT_OK) {
    //                profileViewModel.refreshCreatedAgents()
    //            }
    //        }

    // 创建用于从 Profile 页面创建角色的 launcher（包括从草稿创建）
    //    val createFromProfileLauncher =
    //        rememberLauncherForActivityResult(
    //            contract = ActivityResultContracts.StartActivityForResult()
    //        ) { result ->
    //            // 创建成功后刷新列表和草稿
    //            if (result.resultCode == Activity.RESULT_OK) {
    //                profileViewModel.refreshCreatedAgents()
    //                profileViewModel.refreshAgentDrafts()
    //            }
    //        }

    // 处理从CreateRoleScreen 页面返回的数据
    val currentEntry = navController.currentBackStackEntry
    val savedStateHandle = currentEntry?.savedStateHandle
    val result = savedStateHandle?.getLiveData<Int>("createBackCode")
    LaunchedEffect(result?.value) {
        result?.value?.let {
            if (result.value == Activity.RESULT_OK) {
                // 标记需要刷新 Profile 列表，并切换回 “Me” 页面
                profileViewModel.refreshCreatedAgents()
                profileViewModel.refreshAgentDrafts()
            }
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
            profileViewModel.refreshAgentDrafts()
            profileViewModel.trackPageView("MainPage")
        }
    }

    // 监听从 Create Tab 创建成功后需要刷新的标志
    LaunchedEffect(shouldRefreshProfile) {
        if (shouldRefreshProfile) {
            profileViewModel.refreshCreatedAgents()
            profileViewModel.refreshAgentDrafts()
            onRefreshProfileHandled()
        }
    }

    // 生命周期管理：页面恢复时刷新用户信息，但不频繁刷新列表
    LifecycleResumeEffect(profileViewModel) {
        profileViewModel.loadUserProfile()
        profileViewModel.refreshAgentDrafts()
        VipStatusHelper.refreshSubscriptionStatus()
        // 不再频繁刷新列表，只在首次加载或从 CreateRoleActivity 返回时刷新
        onPauseOrDispose {}
    }

    // 监听用户ID变化，当切换账号时清空并重新加载数据
    var previousUserId by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(uiState.userProfile.id) {
        val currentUserId = uiState.userProfile.id
        // 当用户ID变化且不是首次加载时，清空旧数据并重新加载
        if (
            currentUserId.isNotEmpty() && previousUserId != null && previousUserId != currentUserId
        ) {
            // 用户ID发生变化，清空旧数据并重新加载
            profileViewModel.clearAllData()
            profileViewModel.loadUserProfile()
            profileViewModel.getUserCreatedAgents()
        }
        // 更新上一次的用户ID
        if (currentUserId.isNotEmpty()) {
            previousUserId = currentUserId
        }
    }

    ProfilePage(
        navController,
        modifier = Modifier,
        userProfile = safeUserProfile,
        agents = uiState.userCreatedAgents,
        drafts = uiState.drafts,
        isLoading = uiState.isLoading,
        onClickAgent = { agent ->
            AgentStore.addAgent(agent)
            navController.navigate(Routes.Chat.chatPage(agent.id, false))
        },
        onClickDraft = { draftId ->
            //            val intent = CreateRoleActivity.getIntent(context, null, draftId)
            //            createFromProfileLauncher.launch(intent)
            navController.navigate(Routes.Creat.createRole(draftId))
        },
        onDeleteDraft = { draftId -> profileViewModel.deleteDraft(draftId) },
        onEditAgent = { agent ->
            // 使用 CreateRoleActivity 提供的方法获取 Intent，并监听返回结果
            //            val intent = CreateRoleActivity.getIntent(context, agent)
            //            editAgentLauncher.launch(intent)

            AgentStore.setDraftAgentInfo(agent)
            navController.navigate(Routes.Creat.CreateRole)
        },
        appUpdateTips = appUpdateTips,
        onDeleteAgent = { agent ->
            profileViewModel.deleteAgent(
                agentId = agent.id,
                onSuccess = { /* 删除成功，列表会自动更新 */ },
                onError = { /* 错误处理已在ViewModel中完成 */ },
            )
        },
        onLoadMore = { profileViewModel.loadMoreUserCreatedAgents() },
        profileViewModel = profileViewModel, // 传递 ViewModel 以便 ProfilePage 内部处理刷新
    )
}

// 默认tab的图标配置
private val defaultTabItems =
    listOf(
        HeartBottomTabItem(
            index = 0,
            selectedIcon = R.drawable.tab_icon_home_selected,
            unselectedIcon = R.drawable.tab_icon_chat,
            labelResId = R.string.tab_home,
        ),
        HeartBottomTabItem(
            index = 1,
            selectedIcon = R.drawable.tab_icon_messages_selected,
            unselectedIcon = R.drawable.tab_icon_messages,
            labelResId = R.string.tab_messages,
        ),
        HeartBottomTabItem(
            index = 2,
            selectedIcon = R.drawable.tab_icon_create,
            unselectedIcon = R.drawable.tab_icon_create,
            labelResId = R.string.tab_create,
        ),
        HeartBottomTabItem(
            index = 3,
            selectedIcon = R.drawable.tab_icon_explore_selected,
            unselectedIcon = R.drawable.tab_icon_explore,
            labelResId = R.string.tab_explore,
        ),
        HeartBottomTabItem(
            index = 4,
            selectedIcon = R.drawable.tab_icon_me_selected,
            unselectedIcon = R.drawable.tab_icon_me,
            labelResId = R.string.tab_me,
        ),
    )
