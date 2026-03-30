package com.ai.intellimate

import CheckInRepository
import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.common.event.EventBus
import ai.sxwl.android.common.event.EventSubscriber
import ai.sxwl.android.common.event.PushNotificationEvent
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.GoogleLoginRequest
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.di.networkModule
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FCMConstants
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.firebase.logEvent
import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.content.Intent
import android.view.GestureDetector
import android.view.MotionEvent
import androidx.activity.OnBackPressedCallback
import androidx.activity.viewModels
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavController
import androidx.navigation.compose.rememberNavController
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.call.voiceCallModule
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.explore.flattenAgents
import com.ai.intellimate.explore.isChristmasTheme
import com.ai.intellimate.main.data.SubLimitSignal
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.HolidayCelebrationPopupRules
import com.ai.intellimate.ui.UnlimitChatDialog
import com.ai.intellimate.ui.components.CarouselBackground
import com.ai.intellimate.ui.components.EnterEmailScreen
import com.ai.intellimate.ui.components.GoogleLoginButton
import com.ai.intellimate.ui.components.HolidayCelebrationDialog
import com.ai.intellimate.ui.components.LoginWithEmailScreen
import com.ai.intellimate.ui.components.PolicyText
import com.ai.intellimate.ui.components.RankDialog
import com.ai.intellimate.utils.AgentCacheManager
import com.ai.intellimate.utils.BillingErrorHandler
import com.ai.intellimate.utils.UnifiedStartupManager
import com.ai.intellimate.xb.helper.AgentStore
import com.ai.intellimate.xb.helper.AppConstants.Companion.PUSH_NOTIFICATION
import com.ai.intellimate.xb.navigation.AppNavHost
import com.ai.intellimate.xb.navigation.Routes
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import com.google.android.play.core.review.ReviewInfo
import com.google.android.play.core.review.ReviewManagerFactory
import com.google.android.play.core.review.testing.FakeReviewManager
import kotlin.math.abs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.koin.compose.KoinApplication
import org.koin.core.option.viewModelScopeFactory

/** 主页面，包含聊天、消息与关注、创建模型、模型列表、"我的" */
class MainActivity : BaseActivity() {

    val mainViewModel: MainViewModel by viewModels()
    val chatViewModel: ChatViewModel by viewModels()

    override fun getPageName(): String = "MainPage"

    // 返回拦截相关变量
    private var gestureDetector: GestureDetector? = null
    private val backPressHandler = BackPressHandler()

    // 防重复执行的标志
    private var hasInitializedConfig = false
    private var hasInitializedUserData = false
    private var billingEventCollectJob: Job? = null
    private var hasHandledNotificationIntent = false // 防止重复处理通知 Intent
    private var isAppInForeground = false // App是否在前台

    private val feedbackRequestSubscriber =
        object : EventSubscriber<PushNotificationEvent.MessageReceived> {
            override fun onEvent(event: PushNotificationEvent.MessageReceived) {
                handleFeedbackRequestMessage(event)
            }
        }

    // 延迟时间常量
    private companion object {
        const val DELAY_BILLING_INIT = 500L
        const val DELAY_UPDATE_PLANS = 500L
        const val DELAY_STATE_STABLE = 100L
        const val DELAY_LOGIN_STATE_CHECK = 100L
        const val DELAY_STARTUP_CHECK = 50L

        // 边缘滑动检测常量
        const val EDGE_THRESHOLD = 30 // 边缘检测阈值（像素）
        const val MIN_VELOCITY = 800 // 最小滑动速度
        const val MIN_DISTANCE = 80 // 最小滑动距离
    }

    override fun initConfigData() {
        super.initConfigData()

        // 检查是否从推送通知启动（处理应用在后台时系统自动显示的通知）
        // 如果跳转到 ChatActivity，直接返回，避免执行后续初始化
        if (handleNotificationIntent(intent)) {
            return
        }

        // 防止重复执行（onCreate时会调用一次）
        if (hasInitializedConfig) {
            return
        }

        // 追踪页面访问，包含默认首页 tab
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
        PageTrackingHelper.trackPageView(
            "MainPage",
            "MainActivity",
            mapOf("default_home_tab" to defaultTabName),
        )

        // 设置返回拦截功能
        setupBackInterception()

        // 订阅反馈请求消息
        EventBus.subscribe(PushNotificationEvent.MessageReceived::class, feedbackRequestSubscriber)

        hasInitializedConfig = true

        // 如果用户已登录，立即加载用户数据（应用恢复场景）
        // 如果用户未登录，数据加载会在 LaunchedEffect(isLoggedIn) 中处理
        loadUserDataIfLoggedIn()

        // 用户签到数据初始化
        CheckInRepository.initialize(this)
    }

    /** 检查登录状态是否有效 */
    private suspend fun isUserLoggedIn(): Boolean {
        return IntySetting.isLoginSuspend()
    }

    /** 如果用户已登录，加载用户数据（只执行一次） */
    private fun loadUserDataIfLoggedIn() {
        // 防止重复初始化
        if (hasInitializedUserData) {
            return
        }

        lifecycleScope.launch {
            // 等待启动管理器完成必要初始化（但不等缓存数据）
            while (
                UnifiedStartupManager.startupState.value ==
                    UnifiedStartupManager.StartupState.Initializing
            ) {
                delay(DELAY_STARTUP_CHECK)
            }

            // 检查用户登录状态（不再包括游客用户）
            if (!isUserLoggedIn()) {
                LogUtils.w("MainActivity - 用户未登录，跳过需要认证的数据加载")
                return@launch
            }

            // 标记已初始化，防止重复执行
            hasInitializedUserData = true

            // 加载业务数据（包括版本检查等）
            mainViewModel.loadBusinessData()

            // 初始化 BillingRepository（在用户登录后）
            delay(DELAY_BILLING_INIT)
            BillingRepository.initialize(this@MainActivity)

            // BillingRepository初始化完成后，再调用updatePlans
            delay(DELAY_UPDATE_PLANS)
            mainViewModel.updatePlans()

            // 启动订阅状态监控
            BillingRepository.startEnhancedSubscriptionMonitoring()

            // 监听 Billing 事件并处理 UI 错误提示（只启动一次）
            billingEventCollectJob?.cancel()
            billingEventCollectJob =
                launch(Dispatchers.Main) {
                    BillingRepository.eventFlow.collect { event ->
                        BillingErrorHandler.handleBillingEvent(
                            event,
                            this@MainActivity,
                            this@MainActivity,
                        )
                    }
                }

            // 异步加载用户自建agents（非关键数据），不阻塞启动
            launch(Dispatchers.IO) {
                try {
                    UnifiedStartupManager.syncUserCreatedAgents()
                } catch (e: Exception) {
                    LogUtils.e("MainActivity - 加载用户自建agents失败: ${e.message}")
                }
            }
        }
    }

    /** 重置用户数据初始化标志（用于登出后重新登录） */
    private fun resetUserDataInitialization() {
        hasInitializedUserData = false
        billingEventCollectJob?.cancel()
        billingEventCollectJob = null
    }

    /**
     * 处理从推送通知启动的情况
     *
     * 当应用在后台时，如果服务端发送的是包含 notification 字段的消息， 系统会自动显示通知，点击通知时会启动 MainActivity，并将 data 字段作为 Intent
     * extras 传递。 此方法检查 Intent 中是否包含推送消息的数据，如果有则跳转到 ChatActivity。
     *
     * @param intent 启动 Activity 的 Intent
     * @return 如果已处理并跳转到 ChatActivity，返回 true；否则返回 false
     */
    private fun handleNotificationIntent(intent: Intent?): Boolean {
        if (intent == null) {
            return false
        }

        // 防止重复处理同一个 Intent
        if (hasHandledNotificationIntent) {
            return false
        }

        // 检查 Intent 中是否包含推送消息的数据
        // Firebase 会将 data 字段作为 Intent extras 传递，键名就是 data 中的键名
        val messageType = intent.getStringExtra(FCMConstants.DATA_KEY_TYPE)
        val agentId = intent.getStringExtra(FCMConstants.DATA_KEY_AGENT_ID)

        // 如果没有推送数据，直接返回
        if (messageType == null && agentId == null) {
            return false
        }

        // 节日记忆通知：跳转到该角色 Love Journal 页并定位到对应记忆条目
        if (messageType == FCMConstants.TYPE_FESTIVAL_MEMORY && !agentId.isNullOrEmpty()) {
            hasHandledNotificationIntent = true
            val memoryId =
                if (intent.hasExtra(FCMConstants.DATA_KEY_FESTIVAL_MEMORY_ID)) {
                    intent.getLongExtra(FCMConstants.DATA_KEY_FESTIVAL_MEMORY_ID, 0L)
                } else {
                    null
                }
            FirebaseManager.logEvent(
                FirebaseManager.Events.PUSH_NOTIFICATION_CLICK,
                FirebaseManager.safeEventParams(
                    "agent_id" to agentId,
                    "page_source" to PUSH_NOTIFICATION,
                    "type" to FCMConstants.TYPE_FESTIVAL_MEMORY,
                ),
            )
            mainViewModel.updatePushFestivalMemoryTarget(agentId, memoryId)
            intent.removeExtra(FCMConstants.DATA_KEY_TYPE)
            intent.removeExtra(FCMConstants.DATA_KEY_AGENT_ID)
            intent.removeExtra(FCMConstants.DATA_KEY_FESTIVAL_MEMORY_ID)
            return true
        }

        // 如果是 agent_message 类型且有 agent_id，跳转到 ChatActivity
        if (messageType == FCMConstants.TYPE_AGENT_MESSAGE && !agentId.isNullOrEmpty()) {
            hasHandledNotificationIntent = true // 标记已处理，避免重复跳转
            // 记录推送通知点击事件
            FirebaseManager.logEvent(
                FirebaseManager.Events.PUSH_NOTIFICATION_CLICK,
                FirebaseManager.safeEventParams(
                    "agent_id" to agentId,
                    "page_source" to PUSH_NOTIFICATION,
                ),
            )
            // 跳转到 ChatScreen
            mainViewModel.updatePushAgentId(agentId)

            // 清除 Intent extras，避免重复处理
            intent.removeExtra(FCMConstants.DATA_KEY_TYPE)
            intent.removeExtra(FCMConstants.DATA_KEY_AGENT_ID)
            return true
        }

        // 有推送数据但不是有效的类型，记录日志
        LogUtils.w("MainActivity", "从推送通知启动，但数据不完整 - 消息类型: $messageType, agent_id: $agentId")
        hasHandledNotificationIntent = true
        return false
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()

        KoinApplication(
            application = {
                modules(networkModule, voiceCallModule)
                options(viewModelScopeFactory())
            }
        ) {
            ComposeUI()
        }
    }

    @Composable
    private fun ComposeUI() {
        // 直接使用ViewModel的StateFlow，实现响应式UI更新
        val isLoggedIn by mainViewModel.isLoggedIn.collectAsState()
        val showSettings by mainViewModel.showSettings.collectAsState()
        val selectedTab by mainViewModel.selectedTab.collectAsState()

        // 设计决策：使用会话级标记而非日期级持久化
        // 原因：
        // 1. 每次应用打开都能看到弹窗，增强节日氛围和用户参与度
        // 2. 避免日期格式、时区、跨天等复杂逻辑
        // 3. 性能更好：无需每次检查都读取持久化存储
        // 4. 用户体验：应用重启后可以再次看到，符合"每次打开应用都显示"的需求
        // 避免因恢复Activity而重复显示
        var hasShownInSession by rememberSaveable { mutableStateOf(false) }
        var showHolidayCelebrationDialog by remember { mutableStateOf(false) }
        val themeAgents by AgentCacheManager.themeAgentCache.collectAsState()

        val context = LocalContext.current

        // 设计决策：使用 LaunchedEffect(Unit) 处理应用首次启动的情况
        // 原因：确保应用启动时如果用户已登录，弹窗能够显示
        // 注意：LaunchedEffect(Unit) 只在首次组合时执行一次，不会在应用恢复时重复执行
        LaunchedEffect(Unit) {
            if (isLoggedIn && !hasShownInSession && HolidayCelebrationPopupRules.shouldShowNow()) {
                showHolidayCelebrationDialog = true
                hasShownInSession = true
            }
        }

        // 设计决策：使用 LaunchedEffect(isLoggedIn) 处理登录状态变化
        // 原因：处理用户从未登录变为已登录的情况
        // 注意：通过 hasShownInSession 标记确保每个会话只显示一次，避免与 LaunchedEffect(Unit) 重复
        LaunchedEffect(isLoggedIn) {
            // 场景1：用户从未登录变为已登录，且本次会话未显示过
            if (isLoggedIn && !hasShownInSession && HolidayCelebrationPopupRules.shouldShowNow()) {
                showHolidayCelebrationDialog = true
                hasShownInSession = true
            }
            // 场景2：用户登出
            else if (!isLoggedIn) {
                showHolidayCelebrationDialog = false
                // 设计决策：用户登出时重置会话标记，允许下次登录时再次显示
                // 这确保了每次登录会话都能看到庆祝弹窗
                hasShownInSession = false
            }
            // 场景3：用户已登录且已显示过，或日期已过期，不做任何操作
        }

        LifecycleResumeEffect(Unit) { onPauseOrDispose {} }

        // 在首次显示时执行初始化操作
        LaunchedEffect(Unit) {
            // 1. 实时检查登录状态变化
            // 用于响应：1) 手动logout（在SettingContent中触发） 2) 401自动logout（会重启应用）
            // 注意：onResume() 中也有立即检查，这里作为补充监控
            while (true) {
                val currentState = isUserLoggedIn()
                val viewModelState = mainViewModel.isLoggedIn.value

                if (currentState != viewModelState) {
                    mainViewModel.updateLoginState()
                }

                delay(DELAY_LOGIN_STATE_CHECK)
            }
        }

        // 当登录状态变化时，更新数据加载（只在从未登录变为已登录时执行一次）
        var lastLoggedInState by remember { mutableStateOf(isLoggedIn) }
        var hasInitialized by remember { mutableStateOf(false) }

        LaunchedEffect(isLoggedIn) {
            if (isLoggedIn && !lastLoggedInState && !hasInitialized) {
                lastLoggedInState = true
                hasInitialized = true
                delay(DELAY_STATE_STABLE)
                loadUserDataIfLoggedIn()
            } else if (!isLoggedIn) {
                lastLoggedInState = false
                hasInitialized = false
                resetUserDataInitialization()
            }
        }

        val page = if (isLoggedIn) Routes.HomeTab else Routes.SplashLogin
        // 设计决策：在 MainActivity 中创建 NavController 并传递给 AppNavHost
        // 原因：需要在点击庆祝按钮后导航到随机圣诞角色的聊天页面
        // 通过传递 NavController，MainActivity 可以控制导航，而 AppNavHost 仍然可以在
        // 没有外部 NavController 时创建自己的实例（向后兼容）
        val navController = rememberNavController()
        var mainSubLimitSignal by remember { mutableStateOf<SubLimitSignal?>(null) }

        LaunchedEffect(Unit) {
            mainViewModel.subLimit.collect { signal ->
                when (signal.dialogType) {
                    ChatViewModel.ChatLimitDialogType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.FREE_LIMIT_REACHED,
                            FirebaseManager.safeEventParams(
                                "agent_id" to (signal.sourceAgentId ?: ""),
                                "agent_name" to "",
                                "user_type" to "free",
                                "timestamp" to System.currentTimeMillis(),
                                "source" to "main_websocket",
                            ),
                        )
                    }
                    ChatViewModel.ChatLimitDialogType.SUBSCRIBER_LIMIT_REACHED -> {
                        FirebaseManager.logEvent(
                            FirebaseManager.Events.SUBSCRIBER_LIMIT_REACHED,
                            FirebaseManager.safeEventParams(
                                "agent_id" to (signal.sourceAgentId ?: ""),
                                "agent_name" to "",
                                "user_type" to "vip",
                                "timestamp" to System.currentTimeMillis(),
                                "source" to "main_websocket",
                            ),
                        )
                    }
                }
                mainSubLimitSignal = signal
            }
        }

        val reviewManager = remember {
            if (AppUtils.isAppDebug()) {
                FakeReviewManager(context)
            } else {
                ReviewManagerFactory.create(context)
            }
        }
        var reviewInfo by remember { mutableStateOf<ReviewInfo?>(null) }

        LaunchedEffect(Unit) {
            chatViewModel.showRankDialog.collect {
                LogUtils.d("InAPPReview:ShouldRankRequest")
                reviewManager.requestReviewFlow().addOnCompleteListener { task ->
                    if (task.isSuccessful) {
                        reviewInfo = task.result
                    } else {
                        LogUtils.e(task.exception?.message)
                    }
                }
            }
        }

        reviewInfo?.let { info ->
            RankDialog(
                onCancel = { reviewInfo = null },
                onSubmit = { rank ->
                    if (rank >= 4) {
                        LogUtils.d("InAPPReview:ShouldShowReview")
                        reviewManager
                            .launchReviewFlow(this@MainActivity, info)
                            .addOnCompleteListener {
                                if (it.isSuccessful) {
                                    FirebaseManager.Events.RANK_DIALOG_REVIEW_COMPLETED.logEvent(
                                        "user_id" to IntySetting.getCurUserID()
                                    )
                                }
                            }
                    } else {
                        navController.navigate(Routes.Me.reportPage(isFeedback = true))
                    }
                    reviewInfo = null
                },
            )
        }

        AppNavHost(
            page,
            mainViewModel,
            chatViewModel,
            defaultViewModelProviderFactory,
            navController,
        )

        MainSubLimitDialogLayer(
            signal = mainSubLimitSignal,
            onDismiss = { mainSubLimitSignal = null },
            navController = navController,
        )

        // 只在用户已登录时显示庆祝弹窗
        if (showHolidayCelebrationDialog && isLoggedIn && themeAgents.isNotEmpty()) {
            HolidayCelebrationDialog(
                title = stringResource(R.string.holiday_celebration_title),
                subtitle = stringResource(R.string.holiday_celebration_subtitle),
                primaryButtonText = stringResource(R.string.holiday_celebration_primary_cta),
                onDismiss = { showHolidayCelebrationDialog = false },
                onPrimaryClick = {
                    // 设计决策：点击按钮后执行三个操作：
                    // 1. 添加 100 credits 作为节日奖励（提升用户参与度）
                    // 2. 显示成功提示（即时反馈）
                    // 3. 导航到随机圣诞角色（增强节日主题体验，引导用户探索圣诞内容）
                    LogUtils.d(
                        "MainActivity",
                        "Holiday celebration button clicked, adding 100 credits",
                    )
                    BoostManager.requestManualPoints(100)
                    ToastUtils.showShort(R.string.holiday_celebration_points_added)
                    showHolidayCelebrationDialog = false

                    // 设计决策：使用 isChristmas 标志筛选，而非字符串匹配
                    // 原因：更可靠、性能更好，且由服务端控制，便于维护
                    val christmasThemes = themeAgents.filter { it.isChristmasTheme() }
                    val allChristmasAgents = christmasThemes.flatMap { it.flattenAgents() }

                    if (allChristmasAgents.isNotEmpty()) {
                        // 设计决策：随机选择而非固定选择
                        // 原因：增加趣味性，每次点击可能导航到不同的角色
                        val randomAgent = allChristmasAgents.random()
                        // 设计决策：先添加到 AgentStore，再导航
                        // 原因：确保角色信息已缓存，导航时能正确显示角色信息
                        AgentStore.addAgent(randomAgent)
                        // 设计决策：shouldAutoFocusInput = false
                        // 原因：用户刚进入聊天页面，不应该立即弹出键盘，让用户先看到角色信息
                        navController.navigate(
                            Routes.Chat.chatPage(
                                randomAgent.id,
                                false,
                                shouldAutoFocusInput = false,
                                fromPage = "holiday_celebration",
                            )
                        )
                        LogUtils.d(
                            "MainActivity",
                            "Navigated to Christmas character: ${randomAgent.name} (${randomAgent.id})",
                        )
                    } else {
                        // 设计决策：静默失败，不打扰用户
                        // 原因：这是增强功能，失败不应影响主要流程
                        LogUtils.w("MainActivity", "No Christmas characters found")
                    }
                },
            )
        }

        LaunchedEffect(Unit) {
            BoostManager.pointChanged.collect {
                LogUtils.d("积分变化=${it.first}")
                if (it.first >= 10) {
                    withContext(Dispatchers.Main) {
                        ToastUtils.showShort(R.string.energy_points_add_title, it.first, it.second)
                    }
                }
            }
        }
    }

    /** 设置返回拦截功能 */
    private fun setupBackInterception() {
        // 使用新的OnBackPressedCallback API
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    handleBackPress()
                }
            },
        )

        // 设置边缘滑动手势
        gestureDetector =
            GestureDetector(
                this,
                object : GestureDetector.SimpleOnGestureListener() {
                    override fun onFling(
                        e1: MotionEvent?,
                        e2: MotionEvent,
                        velocityX: Float,
                        velocityY: Float,
                    ): Boolean {
                        if (e1 != null && isEdgeSwipe(e1, e2, velocityX, velocityY)) {
                            handleBackPress()
                            return true
                        }
                        return false
                    }
                },
            )

        // 为根视图设置触摸监听
        window.decorView.setOnTouchListener { _, event ->
            gestureDetector?.onTouchEvent(event) ?: false
        }
    }

    /** 判断是否为边缘滑动 */
    private fun isEdgeSwipe(
        e1: MotionEvent,
        e2: MotionEvent,
        velocityX: Float,
        velocityY: Float,
    ): Boolean {
        // 检查是否从左右边缘开始滑动
        val screenWidth = resources.displayMetrics.widthPixels
        val isFromLeftEdge = e1.x <= EDGE_THRESHOLD
        val isFromRightEdge = e1.x >= screenWidth - EDGE_THRESHOLD

        // 检查滑动距离和速度
        val deltaX = e2.x - e1.x
        val isLeftEdgeSwipe = isFromLeftEdge && deltaX > MIN_DISTANCE && velocityX > MIN_VELOCITY
        val isRightEdgeSwipe =
            isFromRightEdge && deltaX < -MIN_DISTANCE && velocityX < -MIN_VELOCITY

        // 确保是水平滑动（垂直速度不能太大）
        val isHorizontalSwipe = abs(velocityX) > abs(velocityY) * 2

        return (isLeftEdgeSwipe || isRightEdgeSwipe) && isHorizontalSwipe
    }

    /** 处理返回事件（按键返回或手势返回） */
    private fun handleBackPress() {
        // 如果显示设置界面，先关闭设置界面
        if (mainViewModel.showSettings.value) {
            mainViewModel.hideSettings()
            return
        }
        if (mainViewModel.isLoggedIn.value && mainViewModel.navigateBackToPreviousTab()) {
            return
        }
        // 否则按原来的逻辑处理（双击退出）
        backPressHandler.handleBackPress(onExit = { finish() }, onShowHint = { showExitHint() })
    }

    /** 显示退出提示 */
    private fun showExitHint() {
        ToastUtils.showShort(getString(R.string.edge_swipe_exit_hint))
    }

    override fun onResume() {
        super.onResume()
        isAppInForeground = true

        // 检查登录状态变化（用于响应手动logout或401自动logout后的应用重启）
        lifecycleScope.launch {
            val currentLoginState = isUserLoggedIn()
            if (mainViewModel.isLoggedIn.value != currentLoginState) {
                mainViewModel.updateLoginState()
            }

            if (mainViewModel.isLoggedIn.value) {
                BillingRepository.notifyAppResumed()
                chatViewModel.resumeVoicePlayback()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        // 重置通知 Intent 处理标志，允许处理新的 Intent
        hasHandledNotificationIntent = false
        // 处理从推送通知启动的情况（singleTop 模式下会调用此方法）
        handleNotificationIntent(intent)
    }

    override fun onPause() {
        super.onPause()
        isAppInForeground = false
        // 暂停音频播放
        chatViewModel.pauseVoicePlayback()
        // 重置会话消息计数（app 进入后台时清空）
        chatViewModel.resetSessionMessageCount()
    }

    override fun onDestroy() {
        super.onDestroy()
        // 取消订阅反馈请求消息
        EventBus.unsubscribe(
            PushNotificationEvent.MessageReceived::class,
            feedbackRequestSubscriber,
        )
        // 清理返回按键处理器
        backPressHandler.cleanup()
        // 清理 Billing 事件监听
        billingEventCollectJob?.cancel()
        billingEventCollectJob = null
    }

    /** 处理反馈请求消息 */
    private fun handleFeedbackRequestMessage(event: PushNotificationEvent.MessageReceived) {
        if (event.type != FCMConstants.TYPE_FEEDBACK_REQUEST) {
            return
        }

        // 只有在App在前台时才显示弹窗
        if (isAppInForeground) {
            LogUtils.d("MainActivity", "收到 feedback_request 消息，App在前台，显示弹窗")
            mainViewModel.showFeedbackRequestDialog()
        } else {
            LogUtils.d("MainActivity", "收到 feedback_request 消息，App不在前台，不显示弹窗")
        }
    }
}

/**
 * 主 WebSocket [SubLimitSignal] 弹窗：逻辑与旧版 GlobalChatLimitDialog / ChatPage ShowLimitDialog 一致，不经过
 * ChatViewModel.showChatLimitDialog。
 */
@Composable
private fun MainSubLimitDialogLayer(
    signal: SubLimitSignal?,
    onDismiss: () -> Unit,
    navController: NavController,
) {
    signal ?: return
    when (signal.dialogType) {
        ChatViewModel.ChatLimitDialogType.FREE_USER_SUBSCRIPTION_REQUIRED -> {
            val data =
                ChatDialogData(
                    R.drawable.img_unlimit_dialog_bg,
                    stringResource(R.string.str_unlimit_dialog_content),
                    stringResource(R.string.str_unlimit_btn_text),
                )
            UnlimitChatDialog(
                data,
                onCancel = onDismiss,
                onSure = {
                    if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                        navController.navigate(Routes.Me.vipCenter("chat_unlimit_dialog"))
                    }
                    onDismiss()
                },
                onMoreInfo = {
                    if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                        navController.navigate(Routes.Me.vipCenter("chat_unlimit_dialog"))
                    }
                    onDismiss()
                },
            )
        }
        ChatViewModel.ChatLimitDialogType.SUBSCRIBER_LIMIT_REACHED -> {
            AlertDialog(
                onDismissRequest = onDismiss,
                confirmButton = {
                    TextButton(onClick = onDismiss) {
                        Text(text = stringResource(R.string.chat_subscriber_limit_reached_confirm))
                    }
                },
                title = {
                    Text(text = stringResource(R.string.chat_subscriber_limit_reached_title))
                },
                text = {
                    Text(text = stringResource(R.string.chat_subscriber_limit_reached_content))
                },
            )
        }
    }
}

private fun reportLoginFailure(errorType: String, errorMessage: String?, exception: Throwable?) {
    FirebaseManager.logEvent(
        FirebaseManager.Events.AUTH_FAILURE,
        FirebaseManager.safeEventParams(
            "error_type" to errorType,
            "error_message" to (errorMessage?.take(100) ?: "unknown"),
            "login_method" to "google",
        ),
    )
    exception?.let { FirebaseManager.recordException(it, mapOf("error_type" to errorType)) }
}

/** 登录页面状态 */
private enum class LoginScreenState {
    MAIN,
    ENTER_EMAIL,
    LOGIN_WITH_EMAIL,
}

/** Splash 登录界面 - 集成 Google 登录按钮和隐私政策 */
@Composable
fun SplashLoginUI(
    navController: NavController,
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
) {
    val context = LocalContext.current
    var isLoading by remember { mutableStateOf(false) }
    var lastClickTime by remember { mutableLongStateOf(0L) }
    var loginScreenState by remember { mutableStateOf(LoginScreenState.MAIN) }
    var enteredEmail by remember { mutableStateOf("") }
    val coroutineScope = rememberCoroutineScope()

    fun performGoogleSignIn() {
        if (isLoading) return

        val currentTime = System.currentTimeMillis()
        if (!ai.sxwl.android.design.AntiClick.isValidClick(lastClickTime)) return
        lastClickTime = currentTime

        coroutineScope.launch {
            isLoading = true
            try {
                val result =
                    com.ai.intellimate.utils.CredentialManagerHelper.signInWithGoogle(context)
                result.fold(
                    onSuccess = { idToken ->

                        // 直接调用后端登录接口
                        val loginResult =
                            NetServiceMgr.getUserApi()
                                .loginByGoogle(GoogleLoginRequest(idToken = idToken))

                        when (loginResult) {
                            is com.architecture.httplib.core.HttpResult.Success -> {
                                val token = loginResult.data.token
                                val userProfile = loginResult.data.user

                                // ✅ 修复：在登录之前清理 Room 数据库，确保新账号不会看到旧数据
                                // 使用 withContext 确保在 IO 线程执行，并等待完成
                                withContext(Dispatchers.IO) {
                                    try {
                                        ai.sxwl.android.data.di.DataModule.getChatRepository()
                                            .clearAllChatData()
                                        LogUtils.i(
                                            "MainActivity: cleared all chat data before login for user ${userProfile.id}"
                                        )
                                    } catch (e: Exception) {
                                        LogUtils.e(
                                            "MainActivity: failed to clear chat data before login: ${e.message}"
                                        )
                                    }
                                }

                                // 保存用户信息和 token
                                IntySetting.login(userProfile.id, token)
                                com.ai.intellimate.utils.UserProfileManager.saveUserProfile(
                                    userProfile
                                )

                                // 立即设置 Firebase user_id 用户属性（确保后续事件都能关联用户属性）
                                // 注意：只设置 user_id 用户属性，不设置 userType 和 subscriptionLevel
                                // 完整的用户信息（包括 setUserId、userType、subscriptionLevel）会在
                                // UnifiedStartupManager.syncUserProfile() 中通过 setUserInfo() 设置
                                // 这样可以避免设置错误的默认值，防止产生冗余的脏数据
                                FirebaseManager.setUserProperty(
                                    FirebaseManager.UserProperties.USER_ID,
                                    userProfile.id,
                                )

                                // 上报用户登录事件（使用 Firebase 内置 LOGIN 事件）
                                // 注意：由于已设置 user_id 用户属性，会自动关联，但为了 BigQuery 查询方便，仍在参数中包含
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.LOGIN,
                                    FirebaseManager.safeEventParams(
                                        "user_id" to userProfile.id,
                                        "user_name" to (userProfile.nickname),
                                        "login_method" to "google",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )

                                // 登录成功后，主动获取并上报 FCM Token
                                mainViewModel.uploadFCMTokenAfterLogin()

                                // 检查用户信息是否完整（年龄和性别）
                                val needsRegInfo =
                                    userProfile.gender.isNullOrEmpty() ||
                                        userProfile.ageGroup.isNullOrEmpty() ||
                                        userProfile.ageGroup == "<18"

                                // 显示登录成功提示
                                ToastUtils.showShort(R.string.login_successfully)

                                mainViewModel.updateLoginState()
                                UnifiedStartupManager.markUserAccountReady()

                                mainViewModel.updateNeedsRegInfo(needsRegInfo)
                                //                                if (needsRegInfo) {
                                //
                                // com.ai.intellimate.login.RegInfoActivity.launch(context)
                                //                                }
                            }

                            is com.architecture.httplib.core.HttpResult.Failure -> {
                                LogUtils.e("Google login failed: ${loginResult.message}")
                                reportLoginFailure("backend_error", loginResult.message, null)
                                com.ai.intellimate.utils.NetworkErrorHandler.showNetworkAwareError(
                                    context.getString(R.string.network_error)
                                )
                            }
                        }
                    },
                    onFailure = { exception ->
                        when (exception) {
                            is androidx.credentials.exceptions.GetCredentialCancellationException -> {
                                // 用户取消登录，无需处理
                            }

                            is androidx.credentials.exceptions.GetCredentialInterruptedException -> {
                                // 登录过程被中断，无需处理
                            }

                            is GoogleIdTokenParsingException -> {
                                val errorMessage = context.getString(R.string.invalid_google_token)
                                LogUtils.e("Google ID token parsing failed: ${exception.message}")
                                reportLoginFailure(
                                    "token_parsing_error",
                                    exception.message,
                                    exception,
                                )
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }

                            is androidx.credentials.exceptions.NoCredentialException -> {
                                val errorMessage =
                                    context.getString(R.string.no_credentials_available)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                reportLoginFailure("no_credential", errorMessage, exception)
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }

                            is androidx.credentials.exceptions.GetCredentialException -> {
                                val errorMessage = context.getString(R.string.get_credential_failed)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                reportLoginFailure("get_credential_error", errorMessage, exception)
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }

                            else -> {
                                val errorMessage = context.getString(R.string.login_failed)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                reportLoginFailure("unknown_error", exception.message, exception)
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }
                        }
                    },
                )
            } finally {
                isLoading = false
            }
        }
    }

    when (loginScreenState) {
        LoginScreenState.MAIN -> {
            Box(modifier) {
                val bannerText = stringArrayResource(R.array.login_banner_text)
                var bannerIndex by remember { mutableIntStateOf(0) }

                CarouselBackground(
                    imageResIds =
                        listOf(
                            R.drawable.login_banner_0,
                            R.drawable.login_banner_4,
                            R.drawable.login_banner_1,
                            R.drawable.login_banner_5,
                            R.drawable.login_banner_2,
                            R.drawable.login_banner_6,
                            R.drawable.login_banner_3,
                            R.drawable.login_banner_7,
                        ),
                    onPageChange = { bannerIndex = it },
                )
                Column(
                    modifier = Modifier.align(Alignment.BottomCenter),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    val words = remember(bannerIndex) { bannerText[bannerIndex].split(" ") }
                    var wordIndex by remember(bannerIndex) { mutableIntStateOf(0) }
                    val textAlphaAnim = remember { Animatable(0f) }

                    LaunchedEffect(bannerIndex) {
                        for (i in 0 until words.size) {
                            textAlphaAnim.snapTo(0f)

                            wordIndex = i

                            textAlphaAnim.animateTo(targetValue = 1f, animationSpec = tween(350))
                        }
                    }

                    Text(
                        text =
                            buildAnnotatedString {
                                for (i in 0 until wordIndex) {
                                    append(words[i])
                                    append(" ")
                                }

                                withStyle(
                                    style =
                                        SpanStyle(
                                            color = Color.White.copy(alpha = textAlphaAnim.value)
                                        )
                                ) {
                                    append(words[wordIndex])
                                }

                                if (wordIndex < words.size - 1) {
                                    withStyle(SpanStyle(color = Color.Transparent)) {
                                        for (i in wordIndex + 1 until words.size) {
                                            append(" ")
                                            append(words[i])
                                        }
                                    }
                                }
                            },
                        color = Color.White,
                        textAlign = TextAlign.Center,
                        fontSize = 32.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(dimensionResource(R.dimen.padding_large)),
                    )

                    Spacer(Modifier.height(32.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        val dotSizeSelected =
                            dimensionResource(R.dimen.login_carousel_indicator_dot_size_selected)
                        val dotSizeUnselected =
                            dimensionResource(R.dimen.login_carousel_indicator_dot_size_unselected)
                        val dotSpacing =
                            dimensionResource(R.dimen.login_carousel_indicator_dot_spacing)
                        repeat(bannerText.size) { index ->
                            Box(
                                modifier =
                                    Modifier.padding(horizontal = dotSpacing)
                                        .size(
                                            if (index == bannerIndex) dotSizeSelected
                                            else dotSizeUnselected
                                        )
                                        .background(
                                            color =
                                                Color.White.copy(
                                                    alpha = if (index == bannerIndex) 1f else 0.4f
                                                ),
                                            shape = CircleShape,
                                        )
                            )
                        }
                    }
                    Spacer(Modifier.height(32.dp))
                    // Google 登录按钮
                    GoogleLoginButton(
                        isLoading = isLoading,
                        onLoginClick = { performGoogleSignIn() },
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    // Email + Password 登录入口（仅用于审核/测试）
                    androidx.compose.material3.TextButton(
                        onClick = { loginScreenState = LoginScreenState.ENTER_EMAIL },
                        enabled = !isLoading,
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                    ) {
                        androidx.compose.material3.Text(
                            text = stringResource(R.string.continue_with_email),
                            color = Color.White.copy(alpha = 0.35f),
                            fontSize = 12.sp,
                            textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline,
                        )
                    }

                    Box(
                        contentAlignment = Alignment.BottomCenter,
                        modifier =
                            Modifier.height(150.dp)
                                .windowInsetsPadding(WindowInsets.navigationBars)
                                .padding(bottom = 16.dp),
                    ) {

                        // 隐私政策文本
                        PolicyText()
                    }
                }
            }
        }

        LoginScreenState.ENTER_EMAIL -> {
            EnterEmailScreen(
                onBack = { loginScreenState = LoginScreenState.MAIN },
                onContinue = { email ->
                    enteredEmail = email
                    loginScreenState = LoginScreenState.LOGIN_WITH_EMAIL
                },
                initialEmail = enteredEmail,
            )
        }

        LoginScreenState.LOGIN_WITH_EMAIL -> {
            LoginWithEmailScreen(
                email = enteredEmail,
                onBack = { loginScreenState = LoginScreenState.ENTER_EMAIL },
                onLogin = { email, password ->
                    performEmailLogin(email, password, context, mainViewModel, coroutineScope) {
                        isLoading = it
                    }
                },
                isLoading = isLoading,
            )
        }
    }
}

/** Email + Password 登录函数 */
private fun performEmailLogin(
    email: String,
    password: String,
    context: android.content.Context,
    mainViewModel: MainViewModel,
    coroutineScope: CoroutineScope,
    setLoading: (Boolean) -> Unit,
) {
    coroutineScope.launch {
        setLoading(true)
        try {
            val loginResult =
                NetServiceMgr.getUserApi()
                    .loginByGoogle(GoogleLoginRequest(email = email, password = password))

            when (loginResult) {
                is com.architecture.httplib.core.HttpResult.Success -> {
                    val token = loginResult.data.token
                    val userProfile = loginResult.data.user

                    // ✅ 修复：在登录之前清理 Room 数据库，确保新账号不会看到旧数据
                    // 使用 withContext 确保在 IO 线程执行，并等待完成
                    withContext(Dispatchers.IO) {
                        try {
                            ai.sxwl.android.data.di.DataModule.getChatRepository()
                                .clearAllChatData()
                            LogUtils.i(
                                "MainActivity: cleared all chat data before email login for user ${userProfile.id}"
                            )
                        } catch (e: Exception) {
                            LogUtils.e(
                                "MainActivity: failed to clear chat data before email login: ${e.message}"
                            )
                        }
                    }

                    // 保存用户信息和 token
                    IntySetting.login(userProfile.id, token)
                    com.ai.intellimate.utils.UserProfileManager.saveUserProfile(userProfile)

                    // 立即设置 Firebase user_id 用户属性
                    FirebaseManager.setUserProperty(
                        FirebaseManager.UserProperties.USER_ID,
                        userProfile.id,
                    )

                    FirebaseManager.Events.LOGIN.logEvent(
                        "user_id" to userProfile.id,
                        "user_name" to (userProfile.nickname),
                        "login_method" to "email",
                        "timestamp" to System.currentTimeMillis(),
                    )

                    // 登录成功后，主动获取并上报 FCM Token
                    mainViewModel.uploadFCMTokenAfterLogin()

                    // 检查用户信息是否完整（年龄和性别）
                    val needsRegInfo =
                        userProfile.gender.isNullOrEmpty() ||
                            userProfile.ageGroup.isNullOrEmpty() ||
                            userProfile.ageGroup == "<18"

                    // 显示登录成功提示
                    ToastUtils.showShort(R.string.login_successfully)

                    mainViewModel.updateLoginState()
                    UnifiedStartupManager.markUserAccountReady()

                    mainViewModel.updateNeedsRegInfo(needsRegInfo)
                    //                    if (needsRegInfo) {
                    //
                    // com.ai.intellimate.login.RegInfoActivity.launch(context)
                    //                    }
                }

                is com.architecture.httplib.core.HttpResult.Failure -> {
                    LogUtils.e("Email login failed: ${loginResult.message}")
                    reportLoginFailure("backend_error", loginResult.message, null)
                    com.ai.intellimate.utils.NetworkErrorHandler.showNetworkAwareError(
                        context.getString(R.string.network_error)
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e("Email login error: ${e.message}")
            reportLoginFailure("unknown_error", e.message, e)
            ToastUtils.showShort(R.string.login_failed)
        } finally {
            setLoading(false)
        }
    }
}

private class BackPressHandler {
    private var lastBackTime = 0L
    private val backTimeout = 2000L
    private var resetJob: Job? = null

    fun handleBackPress(onExit: () -> Unit, onShowHint: () -> Unit) {
        val currentTime = System.currentTimeMillis()

        when {
            currentTime - lastBackTime <= backTimeout -> {
                onExit()
            }
            else -> {
                onShowHint()
                lastBackTime = currentTime
                scheduleReset()
            }
        }
    }

    private fun scheduleReset() {
        resetJob?.cancel()
        resetJob = CoroutineScope(Dispatchers.Main).launch { delay(backTimeout) }
    }

    fun cleanup() {
        resetJob?.cancel()
    }
}
