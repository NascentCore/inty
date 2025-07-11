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
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.core.content.ContextCompat
import androidx.core.view.GestureDetectorCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.ai.inty.base.BaseActivity
import com.ai.inty.home.HomeScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.ChatViewModel
import com.ai.inty.viewmodels.MainViewModel
import com.inty.utils.log.EasyLog
import com.therouter.router.Autowired
import com.therouter.router.Route
import kotlinx.coroutines.*
import com.ai.inty.billing.BillingRepository

@Route(path = Constant.ROUTE_MAIN)
class MainActivity : BaseActivity() {

    @Autowired
    var action: String = ""

    val mainViewModel: MainViewModel by viewModels()
    val chatViewModel: ChatViewModel by viewModels()

    // 边缘滑动退出相关变量
    private var gestureDetector: GestureDetectorCompat? = null
    private var isFirstSwipe = true
    private var lastSwipeTime = 0L
    private val swipeTimeout = 2000L // 2秒内需要第二次滑动
    private var exitJob: Job? = null

    private val followStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == "FOLLOW_STATE_CHANGED") {
                EasyLog.log("MainActivity received FOLLOW_STATE_CHANGED broadcast")
                val agentId = intent.getStringExtra("agentId")
                val isFollowed = intent.getBooleanExtra("isFollowed", false)
                EasyLog.log("Follow state changed - agentId: $agentId, isFollowed: $isFollowed")
                
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
        
        // Set status bar icons to white for dark theme
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        windowInsetsController.isAppearanceLightStatusBars = false

        // 设置边缘滑动退出功能
        setupEdgeSwipeToExit()

        mainViewModel.setChatViewModel(chatViewModel)
        
        // Load user created agents
        mainViewModel.getUserCreatedAgents()
        
        // 异步更新会员状态
        mainViewModel.updatePlans()

        // 初始化 BillingRepository
        BillingRepository.initialize(this)
        
        setContent {
            IntyTheme {
                HomeScreen(
                    modifier = Modifier.fillMaxSize(),
                    mainViewModel = mainViewModel,
                    chatViewModel = chatViewModel,
                    viewModelFactory = defaultViewModelProviderFactory
                )
//                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
//                    var msg by remember { mutableStateOf("${IntySetting.getCurUserID()} = ${IntySetting.getCurToken()}") }
//                    Column {
//                        Greeting(
//                            name = msg,
//                            modifier = Modifier.padding(innerPadding)
//                        )
//                        Button(onClick = {
//                            IntySetting.changeUser("123")
//                            IntySetting.setToken("token123")
//                        }) {
//                            Text(text = "change user=123")
//                        }
//                        Button(onClick = {
//                            IntySetting.changeUser("guest_123")
//                            IntySetting.setToken("guesttoken123")
//                        }) {
//                            Text(text = "change user=guest")
//                        }
//                        Button(onClick = {
//                            msg = "${IntySetting.getCurUserID()} = ${IntySetting.getCurToken()}"
//                        }) {
//                            Text(text = "get user info")
//                        }
//                        Image(
//                            painter =
//                        )
//
//                        Button(onClick = {
//                            viewModel.createGuest()
//                        }) {
//                            Text(text = "create guest")
//                        }
//                    }
//                }
            }
        }



        requestNotifyPermission()
        
        // Register broadcast receiver
        LocalBroadcastManager.getInstance(this).registerReceiver(
            followStateReceiver,
            IntentFilter("FOLLOW_STATE_CHANGED")
        )
    }

    /**
     * 设置边缘滑动退出功能
     */
    private fun setupEdgeSwipeToExit() {
        gestureDetector = GestureDetectorCompat(this, object : GestureDetector.SimpleOnGestureListener() {
            override fun onFling(
                e1: MotionEvent?,
                e2: MotionEvent,
                velocityX: Float,
                velocityY: Float
            ): Boolean {
                EasyLog.log("MainActivity Fling detected: e1=${e1?.x}, e2=${e2.x}, velocityX=$velocityX, velocityY=$velocityY")
                
                // 检测从左边缘向右滑动
                if (e1 != null && isEdgeSwipe(e1, e2, velocityX, velocityY)) {
                    EasyLog.log("MainActivity Edge swipe confirmed, calling handleEdgeSwipe")
                    handleEdgeSwipe()
                    return true
                }
                return false
            }
        })

        // 为根视图设置触摸监听
        window.decorView.setOnTouchListener { _, event ->
            val result = gestureDetector?.onTouchEvent(event) ?: false
            if (event.action == MotionEvent.ACTION_DOWN || event.action == MotionEvent.ACTION_MOVE || event.action == MotionEvent.ACTION_UP) {
                EasyLog.log("MainActivity Touch event: ${event.action}, x=${event.x}, y=${event.y}, result: $result")
            }
            result
        }
    }

    /**
     * 判断是否为边缘滑动
     */
    private fun isEdgeSwipe(e1: MotionEvent, e2: MotionEvent, velocityX: Float, velocityY: Float): Boolean {
        val edgeThreshold = 30 // 边缘检测阈值（像素）
        val minVelocity = 800 // 最小滑动速度
        val minDistance = 80 // 最小滑动距离
        
        // 检查是否从左边缘开始滑动
        val isFromLeftEdge = e1.x <= edgeThreshold
        
        // 检查滑动距离和速度
        val deltaX = e2.x - e1.x
        val deltaY = e2.y - e1.y
        val isRightSwipe = deltaX > minDistance && velocityX > minVelocity
        
        // 确保是水平滑动（垂直速度不能太大）
        val isHorizontalSwipe = Math.abs(velocityX) > Math.abs(velocityY) * 2
        
        EasyLog.log("MainActivity Edge check: isFromLeftEdge=$isFromLeftEdge, deltaX=$deltaX, deltaY=$deltaY, velocityX=$velocityX, velocityY=$velocityY, isRightSwipe=$isRightSwipe, isHorizontalSwipe=$isHorizontalSwipe")
        
        return isFromLeftEdge && isRightSwipe && isHorizontalSwipe
    }

    /**
     * 处理边缘滑动事件
     */
    private fun handleEdgeSwipe() {
        val currentTime = System.currentTimeMillis()
        EasyLog.log("MainActivity Handling edge swipe: isFirstSwipe=$isFirstSwipe, currentTime=$currentTime")
        
        if (isFirstSwipe) {
            // 第一次滑动，显示提示
            showExitHint()
            isFirstSwipe = false
            lastSwipeTime = currentTime
            
            // 2秒后重置状态
            exitJob?.cancel()
            exitJob = CoroutineScope(Dispatchers.Main).launch {
                delay(swipeTimeout)
                isFirstSwipe = true
                EasyLog.log("MainActivity Edge swipe timeout, reset to first swipe")
            }
        } else {
            // 第二次滑动，检查时间间隔
            if (currentTime - lastSwipeTime <= swipeTimeout) {
                // 在2秒内，执行退出
                EasyLog.log("MainActivity Edge swipe confirmed, exiting activity")
                finish()
            } else {
                // 超过2秒，重新开始
                showExitHint()
                isFirstSwipe = false
                lastSwipeTime = currentTime
                
                exitJob?.cancel()
                exitJob = CoroutineScope(Dispatchers.Main).launch {
                    delay(swipeTimeout)
                    isFirstSwipe = true
                    EasyLog.log("MainActivity Edge swipe timeout, reset to first swipe")
                }
            }
        }
    }

    /**
     * 显示退出提示
     */
    private fun showExitHint() {
        EasyLog.log("MainActivity Showing exit hint toast")
        Toast.makeText(this, getString(R.string.edge_swipe_exit_hint), Toast.LENGTH_SHORT).show()
        EasyLog.log("MainActivity Edge swipe detected, showing exit hint")
    }

    override fun onBackPressed() {
        EasyLog.log("MainActivity onBackPressed")
        
        // 使用边缘滑动防误触逻辑
        handleEdgeSwipe()
    }

    override fun onResume() {
        super.onResume()
        // Refresh following list when returning to MainActivity (e.g., from agent detail page)
        mainViewModel.refreshFollowingListIfOnTab()
        // Refresh created agents list when returning to MainActivity
        mainViewModel.refreshCreatedAgentsListIfOnTab()
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
        val permission = android.Manifest.permission.POST_NOTIFICATIONS

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return
        }
        if (ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED) {
            return
        }

        val requestPermissionLauncher = registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { granted ->
            EasyLog.log("POST_NOTIFICATIONS granted=$granted")
        }
        requestPermissionLauncher.launch(permission)
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(
        text = "Hello $name!",
        modifier = modifier
    )
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    IntyTheme {
        Greeting("Android")
    }
}