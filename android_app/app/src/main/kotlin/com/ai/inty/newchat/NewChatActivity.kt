package com.ai.inty.newchat

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import com.ai.inty.R
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.IChatApi
import com.ai.inty.newchat.data.ChatDataManager
import com.ai.inty.newchat.ui.components.ChatPage
import com.ai.inty.newchat.viewmodel.ChatViewModel
import com.ai.inty.newchat.viewmodel.GlobalChatViewModel
import com.therouter.TheRouter

/**
 * 独立聊天Activity
 * 从Explore页面点击进入，支持返回
 */
class NewChatActivity : ComponentActivity() {

    // 依赖管理
    private lateinit var chatDataManager: ChatDataManager
    private lateinit var globalChatViewModel: GlobalChatViewModel
    private lateinit var chatViewModel: ChatViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val agentId = intent.getStringExtra("agent_id") ?: ""
        val agentName = intent.getStringExtra("agent_name") ?: "聊天"

        // 初始化依赖
        initDependencies()

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    NewChatScreen(
                        agentId = agentId,
                        agentName = agentName,
                        chatViewModel = chatViewModel,
                        onBackClick = { finish() }
                    )
                }
            }
        }
    }

    private fun initDependencies() {
        // 获取网络接口
        val chatApi = TheRouter.get(IChatApi::class.java)
            ?: throw IllegalStateException("IChatApi not found")
        val agentApi = TheRouter.get(IAgentApi::class.java)
            ?: throw IllegalStateException("IAgentApi not found")

        // 创建数据管理器
        chatDataManager = ChatDataManager(chatApi, agentApi)

        // 创建ViewModel
        globalChatViewModel = GlobalChatViewModel(chatDataManager)
        chatViewModel = ChatViewModel(globalChatViewModel, chatDataManager)
    }
}

/**
 * 独立聊天页面内容
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NewChatScreen(
    agentId: String,
    agentName: String,
    chatViewModel: ChatViewModel,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(text = agentName)
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            painter = painterResource(id = R.drawable.back),
                            contentDescription = "返回"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                    navigationIconContentColor = MaterialTheme.colorScheme.onSurface
                )
            )
        }
    ) { innerPadding ->
        ChatPage(
            agentId = agentId,
            agentName = agentName,
            chatViewModel = chatViewModel,
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        )
    }
}
