package com.ai.imate.system.report

import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import com.ai.imate.system.report.data.ReportReasonCode
import com.ai.imate.system.ui.ReportDescriptionContainer
import com.ai.imate.system.ui.ReportImageEvidenceContainer
import com.ai.imate.system.ui.ReportItemRow
import com.ai.imate.system.ui.ReportReasonsContainer
import com.ai.imate.system.ui.ReportSubmitButton

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportScreen(
    modifier: Modifier = Modifier,
    onBack: () -> Unit,
    reasons: List<ReportReasonItem>,
    selectedReasonCodes: Set<ReportReasonCode>,
    onClickReason: (ReportReasonCode, Boolean) -> Unit,
    description: String,
    onDescriptionChange: (String) -> Unit,
    images: List<String>,
    onClickAddImage: () -> Unit,
    onSave: () -> Unit,
    isSubmitting: Boolean,
    isFeedbackMode: Boolean,
) {
    val focusManager = LocalFocusManager.current

    Box(
        modifier =
            modifier.fillMaxSize()
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                ) {
                    focusManager.clearFocus()
                }
    ) {
        Column(
            modifier =
                Modifier.fillMaxSize()
                    .padding(horizontal = 16.dp)
                    .imePadding()
                    .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CenterAlignedTopAppBar(
                title = {},
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )
            Spacer(Modifier.height(16.dp))

            ReportReasonsContainer(
                title =
                    if (isFeedbackMode) {
                        stringResource(R.string.system_feedback_subtitle)
                    } else {
                        stringResource(R.string.system_npc_asterisk_full)
                    }
            ) {
                reasons.forEach { reasonItem ->
                    val isSelected = selectedReasonCodes.contains(reasonItem.reasonCode)
                    val displayText = stringResource(reasonItem.stringResId)
                    ReportItemRow(
                        text = displayText,
                        selected = isSelected,
                        onClick = { onClickReason(reasonItem.reasonCode, !isSelected) },
                    )
                }
            }

            Spacer(Modifier.height(24.dp))

            val requiredDescriptionTitle =
                if (isFeedbackMode) {
                    "${stringResource(R.string.system_feedback_description)} *"
                } else {
                    "${stringResource(R.string.system_report_description)} *"
                }
            ReportDescriptionContainer(
                title = requiredDescriptionTitle,
                description = description,
                onDescriptionChange = onDescriptionChange,
                placeholder =
                    if (isFeedbackMode) {
                        stringResource(R.string.system_feedback_description_placeholder)
                    } else {
                        stringResource(R.string.system_please_fill_feedback_full)
                    },
            )

            Spacer(Modifier.height(24.dp))

            ReportImageEvidenceContainer(
                title = stringResource(R.string.system_image_evidence_full),
                images = images,
                onClickAddImage = onClickAddImage,
            )

            Spacer(Modifier.height(60.dp))

            val canSubmit = selectedReasonCodes.isNotEmpty() && description.trim().isNotEmpty()
            ReportSubmitButton(onSave = onSave, isSubmitting = isSubmitting, enabled = canSubmit)
            Spacer(Modifier.height(60.dp))
        }

        CenterAlignedTopAppBar(
            colors =
                TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1C1523),
                ),
            title = {
                Text(
                    text =
                        if (isFeedbackMode) {
                            stringResource(R.string.system_feedback_title)
                        } else {
                            stringResource(R.string.system_str_report)
                        },
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 20.sp,
                )
            },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = stringResource(R.string.content_desc_back),
                        tint = Color.White,
                    )
                }
            },
        )
    }
}
