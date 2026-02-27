package com.ai.intellimate.agent.report

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.lifecycle.lifecycleScope
import com.ai.intellimate.ViewModelEvent
import kotlinx.coroutines.launch

/** 举报页面 */
@Deprecated("⚠️此Activity 跳转方式已废弃，由Routes.Me.reportPage() 替代")
class ReportActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_TARGET_ID = "intent_key_target_id"
        private const val INTENT_KEY_TARGET_TYPE = "intent_key_target_type"
        private const val INTENT_KEY_IS_FEEDBACK = "intent_key_is_feedback"

        /**
         * 启动举报界面
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
                    intent.putExtra(INTENT_KEY_IS_FEEDBACK, false)
                }
            )
        }

        /**
         * 启动反馈界面
         *
         * @param context 上下文context
         */
        fun launchFeedback(context: Context) {
            context.startActivity(
                Intent(context, ReportActivity::class.java).also { intent ->
                    intent.putExtra(INTENT_KEY_IS_FEEDBACK, true)
                }
            )
        }
    }

    private val viewModel: ReportViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        val isFeedback = intent.getBooleanExtra(INTENT_KEY_IS_FEEDBACK, false)
        viewModel.isFeedbackMode = isFeedback
        viewModel.updateReasonsForMode()

        if (!isFeedback) {
            viewModel.targetID = intent.getStringExtra(INTENT_KEY_TARGET_ID) ?: ""
            viewModel.targetType = intent.getStringExtra(INTENT_KEY_TARGET_TYPE) ?: "USER"
        }

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
        ReportContent(
            viewModel = viewModel,
            onBack = { finish() },
            isFeedbackMode = viewModel.isFeedbackMode,
        )
    }
}

/** 举报内容组件 */
@Composable
private fun ReportContent(viewModel: ReportViewModel, onBack: () -> Unit, isFeedbackMode: Boolean) {
    val reasons = viewModel.reasons.collectAsState()
    val selectedReasonCodes = viewModel.selectedReasonCodes
    val description = viewModel.description.collectAsState()
    val evidenceImages = viewModel.evidenceImagesForDisplay()
    val isSubmitting = viewModel.isSubmitting.collectAsState()

    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
            imageUri?.let { viewModel.onAddImage(imageUri) }
        }

    ReportScreen(
        reasons = reasons.value,
        selectedReasonCodes = selectedReasonCodes,
        onClickReason = { reasonCode, isSelect ->
            LogUtils.i("onClickReason reasonCode = ${reasonCode.name}, isSelect = $isSelect")
            if (isSelect) {
                viewModel.selectedReasonCodes.add(reasonCode)
            } else {
                viewModel.selectedReasonCodes.remove(reasonCode)
            }
        },
        description = description.value,
        onDescriptionChange = { viewModel.setDescription(it) },
        images = evidenceImages,
        onClickAddImage = { galleryLauncher.launch("image/*") },
        onSave = { viewModel.submit() },
        isSubmitting = isSubmitting.value,
        onBack = onBack,
        isFeedbackMode = isFeedbackMode,
    )
}
