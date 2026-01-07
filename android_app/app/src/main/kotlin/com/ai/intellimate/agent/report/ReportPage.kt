package com.ai.intellimate.agent.report

import ai.sxwl.android.utils.LogUtils
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.ViewModelEvent

@Composable
internal fun ReportPage(
    navController: NavController,
    isFeedbackModel: Boolean,
    targetType: String,
    targetId: String,
    prefillDescription: String = "",
    viewModel: ReportViewModel = viewModel(),
) {
    LaunchedEffect(isFeedbackModel, targetType, targetId) {
        viewModel.isFeedbackMode = isFeedbackModel
        viewModel.updateReasonsForMode()
        if (!isFeedbackModel) {
            viewModel.targetID = targetId
            viewModel.targetType = targetType
        }
    }

    LaunchedEffect(prefillDescription) {
        if (prefillDescription.isBlank()) return@LaunchedEffect
        // 仅在 description 为空时填充，避免覆盖用户已输入内容
        if (viewModel.description.value.isBlank()) {
            viewModel.setDescription(prefillDescription)
        }
    }

    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is ViewModelEvent.ReportSubmitted -> {
                    navController.popBackStack()
                }
                else -> {
                    // 其他事件暂不处理
                }
            }
        }
    }

    val reasons = viewModel.reasons.collectAsState()
    val selectedReasonCodes = viewModel.selectedReasonCodes
    val description = viewModel.description.collectAsState()
    val localImages = viewModel.localImages
    val isSubmitting = viewModel.isSubmitting.collectAsState()

    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
            imageUri?.let { viewModel.onAddImage(imageUri) }
        }

    ReportScreen(
        reasons = reasons.value,
        selectedReasonCodes = selectedReasonCodes,
        onClickReason = { reasonCode, isSelect ->
            LogUtils.i("onClickReason reasonCode = ${reasonCode.asString()}, isSelect = $isSelect")
            if (isSelect) {
                viewModel.selectedReasonCodes.add(reasonCode)
            } else {
                viewModel.selectedReasonCodes.remove(reasonCode)
            }
        },
        description = description.value,
        onDescriptionChange = { viewModel.setDescription(it) },
        images = localImages.toList(),
        onClickAddImage = { galleryLauncher.launch("image/*") },
        onSave = { viewModel.submit() },
        isSubmitting = isSubmitting.value,
        onBack = { navController.popBackStack() },
        isFeedbackMode = isFeedbackModel,
    )
}
