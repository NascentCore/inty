package com.ai.inty

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.activity.OnBackPressedCallback
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
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

@Route(path = Constant.ROUTE_MAIN)
class MainActivity : BaseActivity() {

    @Autowired
    var action: String = ""

    val mainViewModel: MainViewModel by viewModels()
    val chatViewModel: ChatViewModel by viewModels()

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

        // Custom back gesture handling - move app to background instead of killing
        val onBackPressedCallback = object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                // Move app to background, don't kill the process
                moveTaskToBack(true)
            }
        }
        onBackPressedDispatcher.addCallback(this, onBackPressedCallback)

        mainViewModel.setChatViewModel(chatViewModel)
        
        // Load user created agents
        mainViewModel.getUserCreatedAgents()
        
        setContent {
            IntyTheme {
                SwipeToExitWrapper(
                    onDoubleSwipeExit = { moveTaskToBack(true) }
                ) {
                    HomeScreen(
                        modifier = Modifier.fillMaxSize(),
                        mainViewModel = mainViewModel,
                        chatViewModel = chatViewModel,
                        viewModelFactory = defaultViewModelProviderFactory
                    )
                }
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

        // Disable both left and right edge system back gestures
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            window.decorView.post {
                val displayMetrics = resources.displayMetrics
                val screenWidth = displayMetrics.widthPixels
                val screenHeight = displayMetrics.heightPixels
                val gestureEdgeSize = (20 * displayMetrics.density).toInt() // 20dp edge
                
                // Exclude both left and right edges from system back gestures
                val leftEdgeRect = Rect(
                    0, // Left edge start
                    0, // Top
                    gestureEdgeSize, // Left edge end
                    screenHeight // Bottom
                )
                
                val rightEdgeRect = Rect(
                    screenWidth - gestureEdgeSize, // Right edge start
                    0, // Top
                    screenWidth, // Right edge end (screen width)
                    screenHeight // Bottom
                )
                
                window.decorView.systemGestureExclusionRects = listOf(leftEdgeRect, rightEdgeRect)
            }
        }

        requestNotifyPermission()
        
        // Register broadcast receiver
        LocalBroadcastManager.getInstance(this).registerReceiver(
            followStateReceiver,
            IntentFilter("FOLLOW_STATE_CHANGED")
        )
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
fun SwipeToExitWrapper(
    onDoubleSwipeExit: () -> Unit,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    
    // Use rememberSaveable to survive configuration changes
    var swipeCount by remember { mutableStateOf(0) }
    var lastSwipeTime by remember { mutableStateOf(0L) }
    val exitSwipeTimeThreshold = 2000L // 2 seconds
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .pointerInput(Unit) {
                var dragStartX = 0f
                var hasDraggedEnough = false
                
                detectHorizontalDragGestures(
                    onDragStart = { offset ->
                        dragStartX = offset.x
                        hasDraggedEnough = false
                    },
                    onDragEnd = {
                        if (hasDraggedEnough) {
                            val currentTime = System.currentTimeMillis()
                            
                            // Check if this is within the time threshold of the last swipe
                            if (swipeCount > 0 && (currentTime - lastSwipeTime) <= exitSwipeTimeThreshold) {
                                // Second swipe - exit app
                                onDoubleSwipeExit()
                            } else {
                                // First swipe - show toast
                                swipeCount = 1
                                lastSwipeTime = currentTime
                                Toast.makeText(
                                    context,
                                    "Swipe again to exit HeartMate",
                                    Toast.LENGTH_SHORT
                                ).show()
                            }
                        }
                    }
                ) { change, dragAmount ->
                    val leftEdgeThreshold = with(density) { 20.dp.toPx() }
                    val minSwipeDistance = with(density) { 100.dp.toPx() }
                    
                    // Only consider left edge swipes moving right
                    if (dragStartX <= leftEdgeThreshold && dragAmount > 0) {
                        val totalDistance = change.position.x - dragStartX
                        if (totalDistance >= minSwipeDistance && !hasDraggedEnough) {
                            hasDraggedEnough = true
                        }
                    }
                }
            }
    ) {
        content()
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