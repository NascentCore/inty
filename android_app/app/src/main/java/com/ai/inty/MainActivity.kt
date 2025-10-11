package com.ai.inty

import android.os.Bundle
import android.view.GestureDetector
import android.view.MotionEvent
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.billing.BillingRepository
import com.ai.inty.chat.ChatViewModel
import com.ai.inty.home.HomeScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.utils.PageTrackingHelper
import com.ai.inty.utils.UnifiedStartupManager
import com.ai.inty.viewmodels.MainViewModel
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.router.Autowired
import com.therouter.router.Route
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.abs

/** 主页面，包含聊天、消息与关注、创建模型、模型列表、"我的" */
@Route(path = Constant.ROUTE_MAIN)
class MainActivity : BaseActivity() {

    @Autowired
    var action: String = ""

    val mainViewModel: MainViewModel by viewModels()
    val chatViewModel: ChatViewModel by viewModels()

    // 返回拦截相关变量
    private var gestureDetector: GestureDetector? = null
    private var isFirstBack = true
    private var lastBackTime = 0L
    private val backTimeout = 2000L // 2秒内需要第二次返回
    private var exitJob: Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        // 不安装系统SplashScreen，完全使用自定义SplashUI
        super.onCreate(savedInstanceState)

        // 追踪页面访问
        PageTrackingHelper.trackPageView("MainActivity", "MainActivity")

        enableEdgeToEdge()

        // 设置状态栏图标为白色
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        windowInsetsController.isAppearanceLightStatusBars = false

        // 设置返回拦截功能
        setupBackInterception()

        mainViewModel.setChatViewModel(chatViewModel)

        // 立即显示UI，不等待启动管理器完成
        // 二次进入应用（进程未被杀）的场景不会再看到自定义 SplashActivity
        lifecycleScope.launch {
            // 等待启动管理器完成必要初始化（但不等缓存数据）
            while (
                UnifiedStartupManager.startupState.value ==
                UnifiedStartupManager.StartupState.Initializing
            ) {
                delay(50) // 50ms检查一次，更快响应
            }

            EasyLog.log("MainActivity - 启动管理器初始化完成，开始加载用户数据")

            // 检查用户登录状态（包括游客用户）
            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                EasyLog.log("MainActivity - 用户已登录（包括游客用户），开始加载业务数据")

                // 加载业务数据（包括版本检查等）
                mainViewModel.loadBusinessData()

                // 异步加载explore agents（不阻塞启动）
                UnifiedStartupManager.loadExploreAgentsAsync()

                // 只有正式用户才加载需要认证的数据
                if (!IntySetting.isGuestUser()) {
                    EasyLog.log("MainActivity - 正式用户，加载需要认证的数据")
                    
                    // Load user created agents
                    mainViewModel.getUserCreatedAgents()

                    // 初始化 BillingRepository（在用户登录后）
                    delay(500) // 给登录流程一些时间
                    BillingRepository.initialize(this@MainActivity)

                    // BillingRepository初始化完成后，再调用updatePlans
                    delay(500) // 给BillingRepository一些初始化时间
                    mainViewModel.updatePlans()

                    // 启动订阅状态监控
                    BillingRepository.startEnhancedSubscriptionMonitoring()
                } else {
                    EasyLog.log("MainActivity - 游客用户，跳过需要认证的数据加载")
                }
            } else {
                EasyLog.log("MainActivity - 用户未登录，跳过需要认证的数据加载", EasyLog.WARN)
            }
        }

        setContent {
            // 手动控制SplashUI显示，类似HeartMate模式
            var showSplash by remember { mutableStateOf(true) }

            IntyTheme {
                if (showSplash) {
                    // 显示自定义SplashUI
                    SplashUI(onSplashComplete = { showSplash = false })
                } else {
                    // 显示主界面
                    HomeScreen(
                        modifier = Modifier.fillMaxSize(),
                        mainViewModel = mainViewModel,
                        chatViewModel = chatViewModel,
                        viewModelFactory = defaultViewModelProviderFactory,
                    )
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
        val currentTime = System.currentTimeMillis()

        if (isFirstBack) {
            // 第一次返回，显示提示
            showExitHint()
            isFirstBack = false
            lastBackTime = currentTime

            // 2秒后重置状态
            exitJob?.cancel()
            exitJob =
                CoroutineScope(Dispatchers.Main).launch {
                    delay(backTimeout)
                    isFirstBack = true
                }
        } else {
            // 第二次返回，检查时间间隔
            if (currentTime - lastBackTime <= backTimeout) {
                // 在2秒内，执行退出
                finish()
            } else {
                // 超过2秒，重新开始
                showExitHint()
                isFirstBack = false
                lastBackTime = currentTime

                exitJob?.cancel()
                exitJob =
                    CoroutineScope(Dispatchers.Main).launch {
                        delay(backTimeout)
                        isFirstBack = true
                    }
            }
        }
    }

    /** 显示退出提示 */
    private fun showExitHint() {
        Toast.makeText(this, getString(R.string.edge_swipe_exit_hint), Toast.LENGTH_SHORT).show()
    }

    override fun onResume() {
        super.onResume()
        // 刷新关注列表和创建的角色列表
        mainViewModel.refreshCreatedAgentsListIfOnTab()
        // 应用恢复时通知billing系统刷新状态
        BillingRepository.notifyAppResumed()
        // 恢复音频播放（如果有正在播放的音频）
        chatViewModel.resumeVoicePlayback()
    }

    override fun onPause() {
        super.onPause()
        // 暂停音频播放
        chatViewModel.pauseVoicePlayback()
    }

    override fun onDestroy() {
        super.onDestroy()
        // 取消协程
        exitJob?.cancel()
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
        Image(
            modifier =
                Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 80.dp)
                    .size(80.dp)
                    .clip(RoundedCornerShape(10.dp)),
            painter = painterResource(R.drawable.icon_splash_icon),
            contentDescription = "",
            contentScale = ContentScale.Crop,
        )
    }
}

/** 等待初始化完成 处理初始化流程中的异常情况，确保即使失败也能进入主界面 */
private suspend fun waitForInitializationComplete(onComplete: () -> Unit) {
    try {
        EasyLog.log("SplashUI - 开始等待初始化完成")

        // 等待启动管理器完成必要初始化
        var waitTime = 0L
        val maxWaitTime = 8000L // 增加等待时间到8秒，确保数据加载完成

        while (
            UnifiedStartupManager.startupState.value ==
            UnifiedStartupManager.StartupState.Initializing && waitTime < maxWaitTime
        ) {
            kotlinx.coroutines.delay(50) // 50ms检查一次
            waitTime += 50
        }

        if (waitTime >= maxWaitTime) {
            EasyLog.log("SplashUI - 等待超时，强制进入主界面", EasyLog.WARN)
        } else {
            EasyLog.log("SplashUI - 启动管理器初始化完成")
        }

        // 等待关键数据加载完成（只等待chat agents）
        EasyLog.log("SplashUI - 等待关键数据chat agents加载完成")
        var dataWaitTime = 0L
        val maxDataWaitTime = 5000L // 最多等待5秒数据加载
        
        while (dataWaitTime < maxDataWaitTime) {
            val hasChatData = UnifiedStartupManager.getCurrentChatAgents().isNotEmpty()
            
            if (hasChatData) {
                EasyLog.log("SplashUI - 关键数据chat agents加载完成: ${UnifiedStartupManager.getCurrentChatAgents().size}个")
                break
            }
            
            delay(100) // 100ms检查一次
            dataWaitTime += 100
        }
        
        if (dataWaitTime >= maxDataWaitTime) {
            EasyLog.log("SplashUI - chat agents数据加载超时，但继续进入主界面", EasyLog.WARN)
        }

        // 标记初始化完成
        UnifiedStartupManager.markEssentialInitializationComplete()

        // 确保有最小显示时间，提供良好的用户体验
        kotlinx.coroutines.delay(1000) // 至少显示1秒

        EasyLog.log("SplashUI - 初始化完成，准备进入主界面")
        onComplete()
    } catch (e: Exception) {
        EasyLog.log("SplashUI - 初始化等待过程中发生异常: ${e.message}", EasyLog.ERROR)
        // 即使发生异常，也要确保进入主界面
        kotlinx.coroutines.delay(500) // 给一点时间显示错误状态
        onComplete()
    }
}
