package com.ai.intellimate.agent.report

import ai.sxwl.android.common.base.BaseActivity
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.lifecycle.lifecycleScope
import com.ai.intellimate.ViewModelEvent
import kotlinx.coroutines.launch

/** 举报页面 */
class ReportActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_TARGET_ID = "intent_key_target_id"
        private const val INTENT_KEY_TARGET_TYPE = "intent_key_target_type"

        /**
         * 启动单独的聊天界面
         *
         * @param context 上下文context
         * @param targetType
         * @param targetId
         */
        fun launch(context: Context, targetType: String = "USER", targetId: String? = null) {
            context.startActivity(
                Intent(context, ReportActivity::class.java).also { intent ->
                    intent.putExtra(INTENT_KEY_TARGET_ID, targetId)
                    intent.putExtra(INTENT_KEY_TARGET_TYPE, targetType)
                }
            )
        }
    }

    private val viewModel: ReportViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        viewModel.updateTarget(
            intent.getStringExtra(INTENT_KEY_TARGET_ID),
            intent.getStringExtra(INTENT_KEY_TARGET_TYPE),
        )

        // 监听ViewModel事件
        lifecycleScope.launch {
            viewModel.events.collect { event ->
                when (event) {
                    is ViewModelEvent.ReportSubmitted -> {
                        finish()
                    }
                    else -> {
                        // 其他事件暂不处理
                    }
                }
            }
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        FeedbackFormContent(viewModel = viewModel, onBack = { finish() })
    }
}
