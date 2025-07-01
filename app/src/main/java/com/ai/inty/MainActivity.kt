package com.ai.inty

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
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

        mainViewModel.setChatViewModel(chatViewModel)
        
        // Load user created agents
        mainViewModel.getUserCreatedAgents()
        
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