package com.ai.imate.system.report

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.imate.system.SystemReportEntry

@Composable
fun SystemReportPage(
    entry: SystemReportEntry,
    onBack: () -> Unit,
    viewModel: ReportViewModel = viewModel(key = "imate_system_report"),
) {
    LaunchedEffect(entry) {
        viewModel.bindEntry(entry)
    }

    LaunchedEffect(Unit) {
        viewModel.submitted.collect { onBack() }
    }

    val reasons by viewModel.reasons.collectAsState()
    val selectedReasonCodes = viewModel.selectedReasonCodes
    val description by viewModel.description.collectAsState()
    val evidenceImages = viewModel.evidenceImagesForDisplay()
    val isSubmitting by viewModel.isSubmitting.collectAsState()

    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
            imageUri?.let { viewModel.onAddImage(it) }
        }

    ReportScreen(
        modifier =
            Modifier.fillMaxSize()
                .background(Color(0xFF1C1523))
                .statusBarsPadding(),
        onBack = onBack,
        reasons = reasons,
        selectedReasonCodes = selectedReasonCodes,
        onClickReason = { reasonCode, isSelect ->
            if (isSelect) {
                viewModel.selectedReasonCodes.add(reasonCode)
            } else {
                viewModel.selectedReasonCodes.remove(reasonCode)
            }
        },
        description = description,
        onDescriptionChange = { viewModel.setDescription(it) },
        images = evidenceImages,
        onClickAddImage = { galleryLauncher.launch("image/*") },
        onSave = { viewModel.submit() },
        isSubmitting = isSubmitting,
        isFeedbackMode = entry.isFeedback,
    )
}
