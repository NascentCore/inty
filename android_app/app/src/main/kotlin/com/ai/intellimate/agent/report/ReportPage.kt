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
    initialEvidenceImageUrl: String,
    viewModel: ReportViewModel = viewModel(),
) {
    LaunchedEffect(isFeedbackModel, targetType, targetId, initialEvidenceImageUrl) {
        viewModel.isFeedbackMode = isFeedbackModel
        viewModel.updateReasonsForMode()
        viewModel.targetID = targetId
        viewModel.targetType = targetType
        viewModel.setInitialEvidenceImage(initialEvidenceImageUrl)
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
        onBack = { navController.popBackStack() },
        isFeedbackMode = isFeedbackModel,
    )
}
