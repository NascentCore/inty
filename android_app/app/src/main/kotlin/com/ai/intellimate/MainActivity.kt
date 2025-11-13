package com.ai.intellimate

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.PermissionUtils
import ai.sxwl.android.utils.ToastUtils
import android.Manifest
import android.os.Build
import android.view.GestureDetector
import android.view.MotionEvent
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
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
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.components.GoogleLoginButton
import com.ai.intellimate.utils.BillingErrorHandler
import com.ai.intellimate.utils.UnifiedStartupManager
import kotlin.math.abs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** 主页面，包含聊天、消息与关注、创建模型、模型列表、"我的" */
class MainActivity : BaseActivity() {

    val mainViewModel: MainViewModel by viewModels()

    override fun getPageName(): String = "MainPage"

    val chatViewModel: ChatViewModel by viewModels()

    // 返回拦截相关变量
    private var gestureDetector: GestureDetector? = null
    private val backPressHandler = BackPressHandler()

    // 防重复执行的标志
    private var hasInitializedConfig = false

    override fun initConfigData() {
        super.initConfigData()

        // 防止重复执行（onCreate时会调用一次，登录成功后可能再调用一次）
        if (hasInitializedConfig) {
            LogUtils.d("MainActivity - initConfigData 已执行过，跳过重复执行")
            return
        }

        // 追踪页面访问
        PageTrackingHelper.trackPageView("MainPage", "MainActivity")

        // 设置返回拦截功能
        setupBackInterception()

        // 申请通知权限（Android 13+）
        requestNotificationPermissionIfNeeded()

        // 标记已初始化（但只标记基本设置，数据加载在登录成功后执行）
        hasInitializedConfig = true

        // 立即显示UI，不等待启动管理器完成
        // 二次进入应用（进程未被杀）的场景不会再看到自定义 SplashActivity
        loadUserDataIfLoggedIn()
    }

    /**
     * 申请通知权限（Android 13+）
     *
     * 如果权限未授予，则主动申请
     */
    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (!PermissionUtils.hasNotificationPermission(this)) {
                // 使用 ActivityResultLauncher 申请权限
                // 注意：这里需要在 Compose 中使用 rememberLauncherForActivityResult
                // 所以实际的权限申请逻辑在 ConfigComposeUI 中实现
                LogUtils.d("MainActivity", "通知权限未授予，将在 Compose UI 中申请")
            } else {
                LogUtils.d("MainActivity", "通知权限已授予")
            }
        } else {
            LogUtils.d("MainActivity", "Android 13 以下版本不需要申请通知权限")
        }
    }

    /** 如果用户已登录，加载用户数据 */
    private fun loadUserDataIfLoggedIn() {
        lifecycleScope.launch {
            // 等待启动管理器完成必要初始化（但不等缓存数据）
            while (
                UnifiedStartupManager.startupState.value ==
                    UnifiedStartupManager.StartupState.Initializing
            ) {
                delay(50) // 50ms检查一次，更快响应
            }

            // 检查用户登录状态（不再包括游客用户）
            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                // 加载业务数据（包括版本检查等）
                mainViewModel.loadBusinessData()

                // 初始化 BillingRepository（在用户登录后）
                delay(500) // 给登录流程一些时间
                BillingRepository.initialize(this@MainActivity)

                // BillingRepository初始化完成后，再调用updatePlans
                delay(500) // 给BillingRepository一些初始化时间
                mainViewModel.updatePlans()

                // 启动订阅状态监控
                BillingRepository.startEnhancedSubscriptionMonitoring()

                // 监听 Billing 事件并处理 UI 错误提示
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
            } else {
                LogUtils.w("MainActivity - 用户未登录，跳过需要认证的数据加载")
            }
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        // 直接使用ViewModel的StateFlow，实现响应式UI更新
        val isLoggedIn by mainViewModel.isLoggedIn.collectAsState()
        val showSettings by mainViewModel.showSettings.collectAsState()

        // 通知权限申请 Launcher（Android 13+）
        val notificationPermissionLauncher =
            rememberLauncherForActivityResult(
                contract = ActivityResultContracts.RequestPermission()
            ) { isGranted ->
                if (isGranted) {
                    LogUtils.i("MainActivity", "通知权限已授予")
                } else {
                    LogUtils.w("MainActivity", "通知权限被拒绝")
                }
            }

        // 在首次显示时执行初始化操作
        LaunchedEffect(Unit) {
            // 1. 检查并申请通知权限（Android 13+）
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                if (!PermissionUtils.hasNotificationPermission(this@MainActivity)) {
                    LogUtils.d("MainActivity", "申请通知权限")
                    notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }

            // 2. 实时检查登录状态变化（用于响应在其他Activity中的logout操作）
            while (true) {
                val currentState = IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                val viewModelState = mainViewModel.isLoggedIn.value

                // 如果实际状态与ViewModel状态不一致，立即更新ViewModel
                if (currentState != viewModelState) {
                    mainViewModel.updateLoginState()
                }

                kotlinx.coroutines.delay(100) // 每100ms检查一次，快速响应logout
            }
        }

        // 当登录状态变化时，更新数据加载（只在从未登录变为已登录时执行一次）
        // 使用 key 避免重复执行：当 isLoggedIn 从未登录变为已登录时才执行
        var lastLoggedInState by remember { mutableStateOf(isLoggedIn) }
        var hasInitialized by remember { mutableStateOf(false) }

        LaunchedEffect(isLoggedIn) {
            // 只在从未登录变为已登录时执行，避免重复触发
            if (isLoggedIn && !lastLoggedInState && !hasInitialized) {
                lastLoggedInState = true
                hasInitialized = true
                kotlinx.coroutines.delay(100) // 小延迟确保状态已稳定
                // 登录成功后，加载用户数据
                loadUserDataIfLoggedIn()
            } else if (!isLoggedIn) {
                lastLoggedInState = false
                hasInitialized = false // 重置，以便下次登录时重新初始化
                // 注意：hideSettings() 应该在 logout() 方法内部调用，而不是在这里调用
                // 这样可以确保状态更新的顺序正确，避免UI闪动
            }
        }

        when {
            !isLoggedIn -> {
                // 用户未登录，显示登录界面
                SplashLoginUI(mainViewModel = mainViewModel)
            }

            showSettings -> {
                // 显示设置界面
                com.ai.intellimate.settings.SettingContent(
                    modifier =
                        Modifier.fillMaxSize()
                            .background(ai.sxwl.android.design.theme.HeartColor.primaryColor),
                    onBack = { mainViewModel.hideSettings() },
                    onLogout = { isDelete ->
                        // 使用MainViewModel的logout方法
                        // logout() 内部已经会调用 hideSettings()，所以不需要在这里再次调用
                        mainViewModel.logout()
                        // 清理 ChatViewModel 数据（在 logout 后）
                        chatViewModel.clearAllData()
                        // 显示退出成功提示
                        val str =
                            if (isDelete) getString(R.string.delete_account_successfully)
                            else getString(R.string.logout_successfully)
                        ai.sxwl.android.utils.ToastUtils.showShort(str)
                        // logout() 内部已经处理了状态更新：
                        // 1. hideSettings() - 关闭设置界面
                        // 2. updateLoginState() - 更新登录状态为false
                        // 这会导致UI从 SettingContent 直接切换到 SplashLoginUI，无闪动
                    },
                )
            }

            else -> {
                // 用户已登录，显示主界面
                HomeScreen(
                    modifier = Modifier.fillMaxSize(),
                    mainViewModel = mainViewModel,
                    viewModelFactory = defaultViewModelProviderFactory,
                )
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
        val edgeThreshold = 30 // 边缘检测阈值（像素）
        val minVelocity = 800 // 最小滑动速度
        val minDistance = 80 // 最小滑动距离

        // 检查是否从左边缘开始滑动
        val isFromLeftEdge = e1.x <= edgeThreshold

        // 检查滑动距离和速度
        val deltaX = e2.x - e1.x
        val isRightSwipe = deltaX > minDistance && velocityX > minVelocity

        // 确保是水平滑动（垂直速度不能太大）
        val isHorizontalSwipe = abs(velocityX) > abs(velocityY) * 2

        return isFromLeftEdge && isRightSwipe && isHorizontalSwipe
    }

    /** 处理返回事件（按键返回或手势返回） */
    private fun handleBackPress() {
        // 如果显示设置界面，先关闭设置界面
        if (mainViewModel.showSettings.value) {
            mainViewModel.hideSettings()
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

        // 立即检查登录状态变化（关键：在onResume时立即检查并更新）
        // 这样可以响应在其他Activity（如SettingActivity）中的logout操作
        // 确保MainActivity恢复时能立即感知状态变化，避免看到旧UI
        val currentLoginState = IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
        if (mainViewModel.isLoggedIn.value != currentLoginState) {
            // 立即更新MainViewModel的状态，触发UI重组
            mainViewModel.updateLoginState()
        }

        // 只有在已登录时才执行这些操作
        if (mainViewModel.isLoggedIn.value) {
            // 应用恢复时通知billing系统刷新状态
            BillingRepository.notifyAppResumed()
            // 恢复音频播放（如果有正在播放的音频）
            chatViewModel.resumeVoicePlayback()
        }
    }

    override fun onPause() {
        super.onPause()
        // 暂停音频播放
        chatViewModel.pauseVoicePlayback()
    }

    override fun onDestroy() {
        super.onDestroy()
        // 清理返回按键处理器
        backPressHandler.cleanup()
    }
}

/** Splash 登录界面 - 集成 Google 登录按钮和隐私政策 */
@Composable
private fun SplashLoginUI(modifier: Modifier = Modifier, mainViewModel: MainViewModel) {
    val context = LocalContext.current
    var isLoading by remember { mutableStateOf(false) }
    var lastClickTime by remember { mutableLongStateOf(0L) }
    val coroutineScope = rememberCoroutineScope()

    // 直接在这里处理登录逻辑，不再依赖 LoginViewModel
    // Google 登录处理
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
                        LogUtils.i("Credential Manager sign-in successful")

                        // 直接调用后端登录接口
                        val userApi = ai.sxwl.android.data.api.NetServiceMgr.getUserApi()
                        val loginResult =
                            userApi.loginByGoogle(
                                ai.sxwl.android.data.api.model.GoogleLoginRequest(idToken = idToken)
                            )

                        when (loginResult) {
                            is com.architecture.httplib.core.HttpResult.Success -> {
                                val token = loginResult.data.token
                                val userProfile = loginResult.data.user

                                // 保存用户信息和 token
                                IntySetting.login(userProfile.id, token)
                                com.ai.intellimate.utils.UserProfileManager.saveUserProfile(
                                    userProfile
                                )

                                // 上报用户登录事件（使用 Firebase 内置 LOGIN 事件）
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

                                // 更新登录状态（用户已经登录成功，只是信息可能不完整）
                                // 这会导致 UI 从 SplashLoginUI 切换到 HomeScreen
                                mainViewModel.updateLoginState()

                                // 标记用户账户已就绪，确保 Explore 等页面可以正常加载数据
                                UnifiedStartupManager.markUserAccountReady()

                                // 异步加载用户自建agents（非关键数据），不阻塞启动
                                coroutineScope.launch(Dispatchers.IO) {
                                    try {
                                        UnifiedStartupManager.syncUserCreatedAgents()
                                    } catch (e: Exception) {
                                        LogUtils.e(
                                            "MainActivity - 登录成功后加载用户自建agents失败: ${e.message}"
                                        )
                                    }
                                }

                                if (needsRegInfo) {
                                    // 需要完善注册信息，跳转到 RegInfo 页面
                                    // 注意：此时 MainActivity 已经显示 HomeScreen，跳转到 RegInfoActivity 后
                                    // RegInfoActivity 完成后，MainActivity 会恢复，状态仍然是已登录，显示 HomeScreen
                                    com.ai.intellimate.login.RegInfoActivity.launch(context)
                                } else {
                                    // 用户信息完整，不需要额外操作，状态已更新，UI 已切换
                                    // onLoginSuccess() 回调可以不执行，因为状态已更新
                                }
                            }

                            is com.architecture.httplib.core.HttpResult.Failure -> {
                                LogUtils.e("Google login failed: ${loginResult.message}")
                                com.ai.intellimate.utils.NetworkErrorHandler.showNetworkAwareError(
                                    loginResult.message
                                )
                            }
                        }
                    },
                    onFailure = { exception ->
                        // 检查是否为用户取消操作，如果是则不显示错误提示
                        when (exception) {
                            is androidx.credentials.exceptions.GetCredentialCancellationException -> {
                                LogUtils.i("User cancelled the login process")
                            }

                            is androidx.credentials.exceptions.GetCredentialInterruptedException -> {
                                LogUtils.i("Login process was interrupted")
                            }

                            is androidx.credentials.exceptions.NoCredentialException -> {
                                val errorMessage =
                                    context.getString(R.string.no_credentials_available)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }

                            is androidx.credentials.exceptions.GetCredentialException -> {
                                val errorMessage = context.getString(R.string.get_credential_failed)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
                                coroutineScope.launch { ToastUtils.showShort(errorMessage) }
                            }

                            else -> {
                                val errorMessage = context.getString(R.string.login_failed)
                                LogUtils.e("Credential Manager sign-in failed: $errorMessage")
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
            GoogleLoginButton(isLoading = isLoading, onLoginClick = { performGoogleSignIn() })

            Spacer(modifier = Modifier.height(24.dp))

            // 隐私政策文本
            com.ai.intellimate.ui.components.PolicyText()

            Spacer(modifier = Modifier.height(80.dp))
        }
    }
}

@Preview
@Composable
private fun SplashUI(modifier: Modifier = Modifier, onSplashComplete: () -> Unit = {}) {
    // 使用LaunchedEffect来执行初始化逻辑
    LaunchedEffect(Unit) {
        // 等待初始化完成
        waitForInitializationComplete(onSplashComplete)
    }

    Box(modifier) {
        Image(
            modifier = Modifier.fillMaxSize(),
            painter = painterResource(R.drawable.app_bg),
            contentScale = ContentScale.Crop,
            alignment = Alignment.TopCenter,
            contentDescription = "",
        )
        Column(
            modifier = Modifier.fillMaxWidth().align(Alignment.BottomCenter),
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
            GoogleLoginButton(isLoading = true, onLoginClick = {})

            Spacer(modifier = Modifier.height(80.dp))
        }
    }
}

/** 等待初始化完成 处理初始化流程中的异常情况，确保即使失败也能进入主界面 */
private suspend fun waitForInitializationComplete(onComplete: () -> Unit) {
    try {
        // 等待启动管理器完成必要初始化
        val maxWaitTime = 5000L // 最多等待5秒
        var waitTime = 0L

        while (
            UnifiedStartupManager.startupState.value ==
                UnifiedStartupManager.StartupState.Initializing && waitTime < maxWaitTime
        ) {
            delay(50)
            waitTime += 50
        }

        if (waitTime >= maxWaitTime) {
            LogUtils.w("SplashUI - 启动管理器等待超时")
        }

        // 等待关键数据加载完成（只等待chat agents）
        waitForChatAgents()

        // 标记初始化完成
        UnifiedStartupManager.markEssentialInitializationComplete()

        // 确保有最小显示时间，提供良好的用户体验
        delay(1000) // 至少显示1秒

        onComplete()
    } catch (e: Exception) {
        LogUtils.e("SplashUI - 初始化等待过程中发生异常: ${e.message}")
        // 即使发生异常，也要确保进入主界面
        delay(500) // 给一点时间显示错误状态
        onComplete()
    }
}

/** 等待聊天角色数据加载完成 */
private suspend fun waitForChatAgents() {
    val maxWaitTime = 5000L // 最多等待5秒
    var waitTime = 0L

    while (waitTime < maxWaitTime) {
        val hasChatData = UnifiedStartupManager.getCurrentChatAgents().isNotEmpty()

        if (hasChatData) {
            LogUtils.d(
                "SplashUI - 关键数据chat agents加载完成: ${UnifiedStartupManager.getCurrentChatAgents().size}个"
            )
            return
        }

        delay(100) // 100ms检查一次
        waitTime += 100
    }

    LogUtils.w("SplashUI - chat agents数据加载超时，但继续进入主界面")
}

/** 返回按键处理器 - 状态机模式 提供优雅的二次确认退出功能 */
private class BackPressHandler {
    private var lastBackTime = 0L
    private val backTimeout = 2000L // 2秒内需要第二次返回
    private var resetJob: Job? = null

    /**
     * 处理返回按键事件
     *
     * @param onExit 退出回调
     * @param onShowHint 显示提示回调
     */
    fun handleBackPress(onExit: () -> Unit, onShowHint: () -> Unit) {
        val currentTime = System.currentTimeMillis()

        when {
            // 在2秒内第二次返回，执行退出
            currentTime - lastBackTime <= backTimeout -> {
                onExit()
            }
            // 第一次返回或超过2秒，显示提示
            else -> {
                onShowHint()
                lastBackTime = currentTime
                scheduleReset()
            }
        }
    }

    /** 调度重置任务 */
    private fun scheduleReset() {
        resetJob?.cancel()
        resetJob =
            CoroutineScope(Dispatchers.Main).launch {
                delay(backTimeout)
                // 2秒后自动重置，允许下次返回
            }
    }

    /** 清理资源 */
    fun cleanup() {
        resetJob?.cancel()
    }
}
