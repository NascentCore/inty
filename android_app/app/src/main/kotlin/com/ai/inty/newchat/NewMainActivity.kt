package com.ai.inty.newchat

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.IChatApi
import com.ai.inty.newchat.data.ChatDataManager
import com.ai.inty.newchat.ui.components.BottomNavigationBar
import com.ai.inty.newchat.ui.screens.ChatTabScreen
import com.ai.inty.newchat.ui.screens.ExploreTabScreen
import com.ai.inty.newchat.viewmodel.ExploreViewModel
import com.therouter.TheRouter

/**
 * 新的主界面Activity
 * 包含Chat和Explore两个Tab
 */
class NewMainActivity : ComponentActivity() {

    // 依赖管理
    private lateinit var chatDataManager: ChatDataManager
    private lateinit var exploreViewModel: ExploreViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // 初始化依赖
        initDependencies()

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    NewMainScreen(
                        chatDataManager = chatDataManager,
                        exploreViewModel = exploreViewModel,
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
        chatDataManager = ChatDataManager(chatApi, agentApi, lifecycleScope)

        // 创建ViewModel
        exploreViewModel = ExploreViewModel(chatDataManager)
    }

    /**
     * 主界面内容
     */
    @Composable
    fun NewMainScreen(
        chatDataManager: ChatDataManager,
        exploreViewModel: ExploreViewModel,
    ) {
        var selectedTab by remember { mutableIntStateOf(0) }

        Scaffold(
            bottomBar = {
                BottomNavigationBar(
                    selectedTab = selectedTab,
                    onTabSelected = { selectedTab = it }
                )
            }
        ) { innerPadding ->
            when (selectedTab) {
                0 -> ChatTabScreen(
                    modifier = Modifier.padding(innerPadding),
                    exploreViewModel = exploreViewModel,
                    chatDataManager = chatDataManager
                )

                1 -> ExploreTabScreen(
                    modifier = Modifier.padding(innerPadding),
                    exploreViewModel = exploreViewModel
                )
            }
        }
    }
}
