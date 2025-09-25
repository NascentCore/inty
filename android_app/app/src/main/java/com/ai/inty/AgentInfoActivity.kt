package com.ai.inty

import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.core.view.WindowCompat
import com.ai.inty.base.BaseActivity
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.screens.AiAgentInfoScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.AgentInfoViewModel
import com.therouter.router.Autowired
import com.therouter.router.Route

/** Ai模型的信息介绍页面 */
@Route(path = Constant.ROUTE_AGENT_INFO)
class AgentInfoActivity : BaseActivity() {

  @Autowired var agent: AgentInfo? = null

  @Autowired var agent_id: String? = null

  val viewModel: AgentInfoViewModel by viewModels()

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    // 强制设置状态栏为白色图标 - 多重保险
    setupStatusBar()

    if (agent == null) {
      if (agent_id != null) {
        viewModel.setAgentID(agent_id!!)
      } else {
        // 既没有 agent 对象也没有 agent_id，说明参数传递有问题
        finish()
        return
      }
    } else {
      viewModel.setAgentInfo(agent)
    }

    setContent {
      IntyTheme {
        val agentInfo = viewModel.agentInfo.collectAsState()
        agentInfo.value?.let { agent -> AiAgentInfoScreen(agent, onBack = { finish() }) }
      }
    }
  }
}

private fun AgentInfoActivity.setupStatusBar() {
  // 使用现代API设置状态栏颜色
  if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
    window.statusBarColor = android.graphics.Color.parseColor("#1C1523")
    window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
  }

  // 使用WindowCompat兼容库统一处理状态栏样式
  WindowCompat.setDecorFitsSystemWindows(window, false)
  val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
  windowInsetsController.isAppearanceLightStatusBars = false
}
