package com.ai.intellimate.agent.info

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import com.ai.intellimate.agent.generate.CreateRoleActivity

/** Ai模型的信息介绍页面 */
class AgentInfoActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_AGENT_ID = "intent_key_agent_id"
        private const val INTENT_KEY_AGENT_INFO = "intent_key_agent_info"

        /**
         * 启动单独的聊天界面
         *
         * @param context 上下文context
         * @param agentInfo Agent的Info对象
         * @param agentId agent的id 两个参数选一即可，也必须只要有一个
         */
        fun launch(context: Context, agentInfo: AgentInfo? = null, agentId: String? = null) {
            context.startActivity(
                Intent(context, AgentInfoActivity::class.java).also { intent ->
                    intent.putExtra(INTENT_KEY_AGENT_ID, agentId)
                    intent.putExtra(INTENT_KEY_AGENT_INFO, agentInfo)
                }
            )
        }
    }

    private var agent: AgentInfo? = null
    private var agentId: String? = null
    private val viewModel: AgentInfoViewModel by viewModels()
    private val editAgentLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                val refreshId = viewModel.agentInfo.value?.id ?: agent?.id ?: agentId
                refreshId?.let { viewModel.setAgentID(it) }
            }
        }

    override fun initConfigData() {
        super.initConfigData()
        agent =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO, AgentInfo::class.java)
            } else {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO)
            }
        agentId = intent.getStringExtra(INTENT_KEY_AGENT_ID)
        if (agent == null) {
            if (agentId != null) {
                viewModel.setAgentID(agentId!!)
            } else {
                // 既没有 agent 对象也没有 agent_id，说明参数传递有问题
                finish()
                return
            }
        } else {
            viewModel.setAgentInfo(agent)
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        val agentInfo = viewModel.agentInfo.collectAsState()
        val galleryImages = viewModel.chatImageGallery.collectAsState()
        agentInfo.value?.let { agent ->
            val currentUserId = IntySetting.getCurUserID()
            val canEdit = IntySetting.isLogin() && currentUserId.isNotEmpty() && agent.creator?.id == currentUserId
            AiAgentInfoScreen(
                agent = agent,
                galleryItems = galleryImages.value,
                onBack = { finish() },
                onEdit = if (canEdit) {
                    {
                        editAgentLauncher.launch(CreateRoleActivity.getIntent(this@AgentInfoActivity, agent))
                    }
                } else {
                    null
                },
            )
        }
    }
}
