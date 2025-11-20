package com.ai.intellimate.agent.report

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState

/**
 * 反馈表单内容容器，复用举报与 Feature Request UI
 */
@Composable
fun FeedbackFormContent(
    viewModel: BaseFeedbackViewModel,
    onBack: () -> Unit,
    titleText: String? = null,
    reasonsTitle: String? = null,
    descriptionTitle: String? = null,
    descriptionPlaceholder: String? = null,
    imageEvidenceTitle: String? = null,
    submitButtonText: String? = null,
) {
    val reasons = viewModel.reasons.collectAsState()
    val description = viewModel.description.collectAsState()
    val isSubmitting = viewModel.isSubmitting.collectAsState()

    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
            imageUri?.let { viewModel.onAddImage(imageUri) }
        }

    ReportScreen(
        reasons = reasons.value,
        selectIDs = viewModel.selectIDS,
        onClickReason = { id, isSelect ->
            if (isSelect) {
                viewModel.selectIDS.add(id)
            } else {
                viewModel.selectIDS.remove(id)
            }
        },
        description = description.value,
        onDescriptionChange = { viewModel.setDescription(it) },
        images = viewModel.localImages.toList(),
        onClickAddImage = { galleryLauncher.launch("image/*") },
        onSave = { viewModel.submit() },
        isSubmitting = isSubmitting.value,
        onBack = onBack,
        titleText = titleText,
        reasonsTitle = reasonsTitle,
        descriptionTitle = descriptionTitle,
        descriptionPlaceholder = descriptionPlaceholder,
        imageEvidenceTitle = imageEvidenceTitle,
        submitButtonText = submitButtonText,
    )
}
