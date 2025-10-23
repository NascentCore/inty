package com.ai.inty

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
import com.ai.inty.base.ViewModelEvent
import com.ai.inty.ui.screens.ReportScreen
import com.ai.inty.viewmodels.ReportViewModel
import kotlinx.coroutines.launch

/** 举报页面 */
class ReportActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_TARGET_ID = "intent_key_target_id"
        private const val INTENT_KEY_TARGET_TYPE = "intent_key_target_type"

        /**
         * 启动单独的聊天界面
         * @param context 上下文context
         * @param targetType
         * @param targetId
         */
        fun launch(context: Context, targetType: String = "USER", targetId: String? = null) {
            context.startActivity(Intent(context, ReportActivity::class.java).also { intent ->
                intent.putExtra(INTENT_KEY_TARGET_ID, targetId)
                intent.putExtra(INTENT_KEY_TARGET_TYPE, targetType)
            })
        }
    }

    private val viewModel: ReportViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        viewModel.targetID = intent.getStringExtra(INTENT_KEY_TARGET_ID) ?: ""
        viewModel.targetType = intent.getStringExtra(INTENT_KEY_TARGET_TYPE) ?: "USER"

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
            onBack = { finish() })
    }
}

/** 举报内容组件 */
@Composable
private fun ReportContent(viewModel: ReportViewModel, onBack: () -> Unit) {
    val reasons = viewModel.reasons.collectAsState()
    val selectIDs = viewModel.selectIDS
    val description = viewModel.description.collectAsState()
    val localImages = viewModel.localImages
    val isSubmitting = viewModel.isSubmitting.collectAsState()

    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
            imageUri?.let { viewModel.onAddImage(imageUri) }
        }

    ReportScreen(
        reasons = reasons.value,
        selectIDs = selectIDs,
        onClickReason = { id, isSelect ->
            LogUtils.i("onClickReason id = $id, isSelect = $isSelect")
            if (isSelect) {
                viewModel.selectIDS.add(id)
            } else {
                viewModel.selectIDS.remove(id)
            }
        },
        description = description.value,
        onDescriptionChange = { viewModel.setDescription(it) },
        images = localImages.toList(),
        onClickAddImage = { galleryLauncher.launch("image/*") },
        onSave = { viewModel.submit() },
        isSubmitting = isSubmitting.value,
        onBack = onBack,
    )
}
