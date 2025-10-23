package com.ai.intellimate

import ai.sxwl.android.common.base.BaseActivity
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.ai.intellimate.chat.data.ChatDataManager
import com.ai.intellimate.chat.di.NewChatDI
import com.ai.intellimate.chat.ui.components.BottomNavigationBar
import com.ai.intellimate.chat.ui.screens.ChatTabScreen
import com.ai.intellimate.chat.ui.screens.ExploreTabScreen
import com.ai.intellimate.chat.viewmodel.ChatTabViewModel
import com.ai.intellimate.chat.viewmodel.ExploreViewModel

/**
 * 新的主界面Activity
 * 包含Chat和Explore两个Tab
 */
class NewMainActivity : BaseActivity() {

    // 依赖管理
    private lateinit var chatDataManager: ChatDataManager
    private lateinit var chatTabViewModel: ChatTabViewModel
    private lateinit var exploreViewModel: ExploreViewModel


    override fun initConfigData() {
        super.initConfigData()
        // 初始化依赖
        initDependencies()
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        NewMainScreen(
            chatDataManager = chatDataManager,
            chatTabViewModel = chatTabViewModel,
            exploreViewModel = exploreViewModel,
        )
    }

    private fun initDependencies() {
        // 获取 newchat 模块内共享的单例数据管理器
        chatDataManager = NewChatDI.chatDataManager

        // 创建ViewModel
        chatTabViewModel = ChatTabViewModel(chatDataManager)
        exploreViewModel = ExploreViewModel(chatDataManager)
    }

    /**
     * 主界面内容
     */
    @Composable
    fun NewMainScreen(
        chatDataManager: ChatDataManager,
        chatTabViewModel: ChatTabViewModel,
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
                    modifier = Modifier.Companion.padding(innerPadding),
                    chatTabViewModel = chatTabViewModel,
                    chatDataManager = chatDataManager
                )

                1 -> ExploreTabScreen(
                    modifier = Modifier.Companion.padding(innerPadding),
                    exploreViewModel = exploreViewModel
                )
            }
        }
    }
}
