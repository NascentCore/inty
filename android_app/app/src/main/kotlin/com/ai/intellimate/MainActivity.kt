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
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FCMConstants
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.content.Intent
import android.view.GestureDetector
import android.view.MotionEvent
import androidx.activity.OnBackPressedCallback
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.navigation.NavController
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.http.services.AgentService
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.xb.helper.AgentStore
import kotlin.random.Random
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.HolidayCelebrationPopupRules
import com.ai.intellimate.ui.components.HolidayCelebrationDialog
import com.ai.intellimate.ui.components.EmailLoginButton
import com.ai.intellimate.ui.components.EnterEmailScreen
import com.ai.intellimate.ui.components.GoogleLoginButton
import com.ai.intellimate.ui.components.LoginWithEmailScreen
import com.ai.intellimate.utils.BillingErrorHandler
import com.ai.intellimate.utils.UnifiedStartupManager
import com.ai.intellimate.xb.helper.AppConstants.Companion.PUSH_NOTIFICATION
import com.ai.intellimate.xb.navigation.AppNavHost
import com.ai.intellimate.xb.navigation.Routes
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import kotlin.math.abs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

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
            } catch (e: Exception) {
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
    private fun isUserLoggedIn(): Boolean {
        return IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
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
        } else {
            // 有推送数据但不是有效的 agent_message，记录日志
            LogUtils.w("MainActivity", "从推送通知启动，但数据不完整 - 消息类型: $messageType, agent_id: $agentId")
            // 标记已处理，避免重复检查
            hasHandledNotificationIntent = true
            return false
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        // 直接使用ViewModel的StateFlow，实现响应式UI更新
        val isLoggedIn by mainViewModel.isLoggedIn.collectAsState()
        val showSettings by mainViewModel.showSettings.collectAsState()

        var showHolidayCelebrationDialog by remember { mutableStateOf(false) }
        LifecycleResumeEffect(Unit) {
            // 每次应用打开/回到前台时，如果用户已登录，就显示庆祝弹窗
            showHolidayCelebrationDialog = isLoggedIn && HolidayCelebrationPopupRules.shouldShowNow()
            onPauseOrDispose {}
        }
        // 当用户登录状态变化时，检查是否需要显示庆祝弹窗
        LaunchedEffect(isLoggedIn) {
            if (isLoggedIn && HolidayCelebrationPopupRules.shouldShowNow()) {
                showHolidayCelebrationDialog = true
            } else if (!isLoggedIn) {
                showHolidayCelebrationDialog = false
            }
        }

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

        //        when {
        //            !isLoggedIn -> {
        //                // 用户未登录，显示登录界面
        //                SplashLoginUI(mainViewModel = mainViewModel)
        //            }
        //
        //            showSettings -> {
        //                // 显示设置界面
        //                com.ai.intellimate.settings.SettingScreen(
        //                    modifier =
        //                        Modifier.fillMaxSize()
        //
        // .background(ai.sxwl.android.design.theme.HeartColor.primaryColor),
        //                    onBack = { mainViewModel.hideSettings() },
        //                    onLogout = { isDelete ->
        //                        mainViewModel.logout()
        //                        chatViewModel.clearAllData()
        //                        val str =
        //                            if (isDelete) getString(R.string.delete_account_successfully)
        //                            else getString(R.string.logout_successfully)
        //                        ai.sxwl.android.utils.ToastUtils.showShort(str)
        //                    },
        //                )
        //            }
        //
        //            else -> {
        //                // 用户已登录，显示主界面
        //                HomeScreen(
        //                    modifier = Modifier.fillMaxSize(),
        //                    mainViewModel = mainViewModel,
        //                    viewModelFactory = defaultViewModelProviderFactory,
        //                )
        //            }
        //        }
        val page = if (isLoggedIn) Routes.HomeTab else Routes.SplashLogin
        val navController = rememberNavController()
        val scope = rememberCoroutineScope()
        AppNavHost(page, mainViewModel, chatViewModel, defaultViewModelProviderFactory, navController)

        // 只在用户已登录时显示庆祝弹窗
        if (showHolidayCelebrationDialog && isLoggedIn) {
            HolidayCelebrationDialog(
                title = stringResource(R.string.holiday_celebration_title),
                subtitle = stringResource(R.string.holiday_celebration_subtitle),
                primaryButtonText = stringResource(R.string.holiday_celebration_primary_cta),
                onDismiss = { showHolidayCelebrationDialog = false },
                onPrimaryClick = {
                    // 添加100个boost points作为节日奖励
                    LogUtils.d("MainActivity", "Holiday celebration button clicked, adding 100 boost points")
                    BoostManager.requestManualPoints(100)
                    ToastUtils.showShort(R.string.holiday_celebration_points_added)
                    showHolidayCelebrationDialog = false
                    
                    // 随机打开一个圣诞主题角色的聊天页面
                    scope.launch {
                        try {
                            val themesResult = AgentService.getCharacterThemes(limit = 100)
                            if (themesResult is ai.sxwl.android.data.http.ApiResult.Success) {
                                val christmasThemes = themesResult.data.filter { it.isChristmas }
                                val allChristmasAgents = christmasThemes.flatMap { it.agents }
                                
                                if (allChristmasAgents.isNotEmpty()) {
                                    val randomAgent = allChristmasAgents[Random.nextInt(allChristmasAgents.size)]
                                    AgentStore.addAgent(randomAgent)
                                    navController.navigate(Routes.chatPage(randomAgent.id, false, shouldAutoFocusInput = false))
                                    LogUtils.d("MainActivity", "Navigated to Christmas character: ${randomAgent.name} (${randomAgent.id})")
                                } else {
                                    LogUtils.w("MainActivity", "No Christmas characters found")
                                }
                            } else {
                                LogUtils.e("MainActivity", "Failed to get character themes")
                            }
                        } catch (e: Exception) {
                            LogUtils.e("MainActivity", "Error getting Christmas characters: ${e.message}", e)
                        }
                    }
                },
            )
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
        val currentLoginState = isUserLoggedIn()
        if (mainViewModel.isLoggedIn.value != currentLoginState) {
            mainViewModel.updateLoginState()
        }

        if (mainViewModel.isLoggedIn.value) {
            BillingRepository.notifyAppResumed()
            chatViewModel.resumeVoicePlayback()
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

                                if (needsRegInfo) {
                                    com.ai.intellimate.login.RegInfoActivity.launch(context)
                                }
                            }

                            is com.architecture.httplib.core.HttpResult.Failure -> {
                                LogUtils.e("Google login failed: ${loginResult.message}")
                                reportLoginFailure("backend_error", loginResult.message, null)
                                com.ai.intellimate.utils.NetworkErrorHandler.showNetworkAwareError(
                                    loginResult.message
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
                Image(
                    modifier = Modifier.fillMaxSize(),
                    painter = painterResource(R.drawable.app_bg),
                    contentScale = ContentScale.Crop,
                    alignment = Alignment.TopCenter,
                    contentDescription = "",
                )
                Column(
                    modifier = Modifier.align(Alignment.BottomCenter),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Image(
                        modifier = Modifier.size(120.dp).clip(RoundedCornerShape(10.dp)),
                        painter = painterResource(R.drawable.icon_splash_icon),
                        contentDescription = "",
                        contentScale = ContentScale.Crop,
                    )
                    Spacer(modifier = Modifier.height(120.dp))

                    // Google 登录按钮
                    GoogleLoginButton(
                        isLoading = isLoading,
                        onLoginClick = { performGoogleSignIn() },
                    )

                    Spacer(modifier = Modifier.height(24.dp))

                    // Email 登录按钮
                    EmailLoginButton(
                        isLoading = isLoading,
                        onLoginClick = { loginScreenState = LoginScreenState.ENTER_EMAIL },
                    )

                    Spacer(modifier = Modifier.height(24.dp))

                    // 隐私政策文本
                    com.ai.intellimate.ui.components.PolicyText()

                    Spacer(modifier = Modifier.height(80.dp))
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

                    // 上报用户登录事件
                    FirebaseManager.logEvent(
                        FirebaseManager.Events.LOGIN,
                        FirebaseManager.safeEventParams(
                            "user_id" to userProfile.id,
                            "user_name" to (userProfile.nickname),
                            "login_method" to "email",
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

                    if (needsRegInfo) {
                        com.ai.intellimate.login.RegInfoActivity.launch(context)
                    }
                }

                is com.architecture.httplib.core.HttpResult.Failure -> {
                    LogUtils.e("Email login failed: ${loginResult.message}")
                    reportLoginFailure("backend_error", loginResult.message, null)
                    com.ai.intellimate.utils.NetworkErrorHandler.showNetworkAwareError(
                        loginResult.message
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
