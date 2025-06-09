package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.ai.inty.base.BaseActivity
import com.ai.inty.beans.AgentInfo
import com.ai.inty.chat.ChatPage
import com.ai.inty.home.HomeScreen
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.ChatViewModel
import com.ai.inty.viewmodels.MainViewModel
import com.therouter.router.Autowired
import com.therouter.router.Route

@Route(path = Constant.ROUTE_CHAT)
class ChatActivity : BaseActivity() {

    @Autowired
    var agent: AgentInfo? = null

    @Autowired
    var agent_id: String? = null

    val chatViewModel: ChatViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        if (agent == null) {
            chatViewModel.setAgentID(agent_id!!)
        } else {
            chatViewModel.setAgentInfo(agent)
        }

        setContent {
            IntyTheme {
                ChatPage(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(BackGround),
                    chatViewModel = chatViewModel
                )
            }
        }
    }
}
