package com.ai.inty

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.GestureDetector
import android.view.MotionEvent
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.lifecycle.lifecycleScope
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import com.ai.inty.base.BaseActivity

import com.ai.inty.billing.BillingRepository
import com.ai.inty.home.HomeScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.ChatViewModel
import com.ai.inty.viewmodels.MainViewModel
import com.inty.utils.log.EasyLog
import com.therouter.router.Autowired
import com.therouter.router.Route
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.abs

/**
 * 主页面，包含聊天、消息与关注、创建模型、模型列表、"我的"
 */
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

    // 关注状态变化的 广播接收器
    private val followStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == "FOLLOW_STATE_CHANGED") {
                EasyLog.log("MainActivity received FOLLOW_STATE_CHANGED broadcast")
                val agentId = intent.getStringExtra("agentId")
                val isFollowed = intent.getBooleanExtra("isFollowed", false)

                // 强制刷新关注列表
                mainViewModel.refreshFollowingListIfOnTab()

                // 同时更新主列表中的agent状态
                agentId?.let { id ->
                    mainViewModel.updateAgentFollowStateInList(id, isFollowed)
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        enableEdgeToEdge()

        // 设置状态栏图标为白色
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        windowInsetsController.isAppearanceLightStatusBars = false

        // 设置返回拦截功能
        setupBackInterception()

        mainViewModel.setChatViewModel(chatViewModel)

        // Load user created agents
        mainViewModel.getUserCreatedAgents()

        // 初始化 BillingRepository（在用户登录后）
        lifecycleScope.launch {
            // 等待用户登录完成
            delay(1000) // 给登录流程一些时间

            // 执行billing诊断
//            val diagnosticReport =
//                BillingDiagnosticHelper.performBillingDiagnostic(this@MainActivity)
//            EasyLog.log("MainActivity - Billing诊断报告: $diagnosticReport")

            BillingRepository.initialize(this@MainActivity)

            // BillingRepository初始化完成后，再调用updatePlans
            delay(500) // 给BillingRepository一些初始化时间
            mainViewModel.updatePlans()

            // 启动订阅状态监控
            BillingRepository.startEnhancedSubscriptionMonitoring()
        }

        setContent {
            IntyTheme {
                HomeScreen(
                    modifier = Modifier.fillMaxSize(),
                    mainViewModel = mainViewModel,
                    chatViewModel = chatViewModel,
                    viewModelFactory = defaultViewModelProviderFactory
                )
            }
        }

        requestNotifyPermission()

        // 注册广播接收器
        LocalBroadcastManager.getInstance(this).registerReceiver(
            followStateReceiver,
            IntentFilter("FOLLOW_STATE_CHANGED")
        )
    }

    /**
     * 设置返回拦截功能
     */
    private fun setupBackInterception() {
        // 使用新的OnBackPressedCallback API
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                handleBackPress()
            }
        })

        // 设置边缘滑动手势
        gestureDetector = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
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
        })

        // 为根视图设置触摸监听
        window.decorView.setOnTouchListener { _, event ->
            gestureDetector?.onTouchEvent(event) ?: false
        }
    }

    /**
     * 判断是否为边缘滑动
     */
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

    /**
     * 处理返回事件（按键返回或手势返回）
     */
    private fun handleBackPress() {
        val currentTime = System.currentTimeMillis()

        if (isFirstBack) {
            // 第一次返回，显示提示
            showExitHint()
            isFirstBack = false
            lastBackTime = currentTime

            // 2秒后重置状态
            exitJob?.cancel()
            exitJob = CoroutineScope(Dispatchers.Main).launch {
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
                exitJob = CoroutineScope(Dispatchers.Main).launch {
                    delay(backTimeout)
                    isFirstBack = true
                }
            }
        }
    }

    /**
     * 显示退出提示
     */
    private fun showExitHint() {
        Toast.makeText(this, getString(R.string.edge_swipe_exit_hint), Toast.LENGTH_SHORT).show()
    }


    override fun onResume() {
        super.onResume()
        // 刷新关注列表和创建的角色列表
        mainViewModel.refreshFollowingListIfOnTab()
        mainViewModel.refreshCreatedAgentsListIfOnTab()
        // 应用恢复时通知billing系统刷新状态
        BillingRepository.notifyAppResumed()
    }

    override fun onDestroy() {
        super.onDestroy()

        // 释放 BillingRepository 资源
        BillingRepository.release()

        // 取消协程
        exitJob?.cancel()

        // Unregister broadcast receiver
        LocalBroadcastManager.getInstance(this).unregisterReceiver(followStateReceiver)
    }

    private fun requestNotifyPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return

        if (ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val requestPermissionLauncher = registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { granted ->
            EasyLog.log("POST_NOTIFICATIONS granted=$granted")
        }
        requestPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
    }
}
