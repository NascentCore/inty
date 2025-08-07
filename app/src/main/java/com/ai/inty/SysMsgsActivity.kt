package com.ai.inty

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import com.ai.inty.ui.screens.SysMsgsScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.SysMsgViewModel
import com.therouter.router.Route

/**
 * 系统消息页面
 */
@Route(path = Constant.ROUTE_SYS_MSGS)
class SysMsgsActivity : ComponentActivity() {

    private val viewModel: SysMsgViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            IntyTheme {
                SysMsgsContent(
                    msgs = viewModel.sysMsgs,
                    onBack = { finish() }
                )
            }
        }
    }
}

/**
 * 系统消息内容组件
 */
@Composable
private fun SysMsgsContent(
    msgs: List<com.ai.inty.beans.SysMsgItem>,
    onBack: () -> Unit
) {
    SysMsgsScreen(
        msgs = msgs,
        onBack = onBack
    )
}
