package com.ai.intellimate.agent.report

import ai.sxwl.android.data.api.model.ReportItem
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.Image
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
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.ReportDescriptionContainer
import com.ai.intellimate.ui.components.ReportImageEvidenceContainer
import com.ai.intellimate.ui.components.ReportItem
import com.ai.intellimate.ui.components.ReportReasonsContainer
import com.ai.intellimate.ui.components.SaveBtn

/** 举报屏幕 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportScreen(
    onBack: () -> Unit = {},
    reasons: List<ReportItem>,
    selectIDs: Set<Int>,
    onClickReason: (Int, Boolean) -> Unit,
    description: String,
    onDescriptionChange: (String) -> Unit,
    images: List<String>,
    onClickAddImage: () -> Unit,
    onSave: () -> Unit,
    isSubmitting: Boolean = false,
    pageType: ReportMode = ReportMode.REPORT,
) {
    val focusManager = LocalFocusManager.current

    Box(
        modifier =
            Modifier.fillMaxSize().clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
            ) {
                focusManager.clearFocus()
            }
    ) {
        Column(
            modifier =
                Modifier.matchParentSize()
                    .padding(horizontal = 16.dp)
                    .imePadding()
                    .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // 布局占位用
            CenterAlignedTopAppBar(
                title = {},
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )
            Spacer(Modifier.height(16.dp))

            // 举报原因或反馈选项
            val reasonTitle =
                when (pageType) {
                    ReportMode.REPORT -> stringResource(R.string.npc_asterisk_full)
                    ReportMode.FEEDBACK -> stringResource(R.string.tell_us_what_you_think)
                    ReportMode.FEATURE_REQUEST ->
                        stringResource(R.string.feature_request_category_title)
                }
            ReportReasonsContainer(title = reasonTitle) {
                reasons.forEach { reason ->
                    val isSelected = selectIDs.contains(reason.id)
                    val displayText =
                        when (pageType) {
                            ReportMode.REPORT ->
                                when (reason.code) {
                                    "SENSITIVE_CONTENT" ->
                                        stringResource(R.string.report_reason_sensitive_content)
                                    "MISINFORMATION" ->
                                        stringResource(R.string.report_reason_misinformation)
                                    "FRAUD_SCAMS" ->
                                        stringResource(R.string.report_reason_fraud_scams)
                                    "PRIVACY_VIOLATION" ->
                                        stringResource(R.string.report_reason_privacy_violation)
                                    "HARMFUL_MINORS" ->
                                        stringResource(R.string.report_reason_harmful_minors)
                                    "IP_VIOLATION" ->
                                        stringResource(R.string.report_reason_ip_violation)
                                    "OTHER" -> stringResource(R.string.report_reason_other)
                                    else -> reason.description
                                }
                            ReportMode.FEEDBACK ->
                                when (reason.code) {
                                    "CHAT_NOT_NATURAL" ->
                                        stringResource(R.string.feedback_reason_chat_not_natural)
                                    "CHARACTER_MISMATCH" ->
                                        stringResource(R.string.feedback_reason_character_mismatch)
                                    "APP_SLOW" ->
                                        stringResource(R.string.feedback_reason_app_slow)
                                    "FEATURE_HARD_TO_FIND" ->
                                        stringResource(R.string.feedback_reason_feature_hard_to_find)
                                    "UI_INCONVENIENT" ->
                                        stringResource(R.string.feedback_reason_ui_inconvenient)
                                    "NEW_FEATURE" ->
                                        stringResource(R.string.feedback_reason_new_feature)
                                    "OTHER" -> stringResource(R.string.feedback_reason_other)
                                    else -> reason.description
                                }
                            ReportMode.FEATURE_REQUEST ->
                                when (reason.code) {
                                    "FEATURE_UI" ->
                                        stringResource(R.string.feature_category_ui)
                                    "FEATURE_AI_CHARACTER" ->
                                        stringResource(R.string.feature_category_ai_character)
                                    "FEATURE_AI_MODELS" ->
                                        stringResource(R.string.feature_category_ai_models)
                                    "FEATURE_VOICE" ->
                                        stringResource(R.string.feature_category_voice)
                                    "FEATURE_IMAGE" ->
                                        stringResource(R.string.feature_category_image)
                                    "FEATURE_SUBSCRIPTION" ->
                                        stringResource(R.string.feature_category_subscription)
                                    "FEATURE_OTHERS" ->
                                        stringResource(R.string.feature_category_others)
                                    else -> reason.description
                                }
                        }
                    ReportItem(
                        text = displayText,
                        selected = isSelected,
                        onClick = { onClickReason(reason.id, !isSelected) },
                    )
                }
            }

            Spacer(Modifier.height(24.dp))

            // 举报描述或反馈描述
            val descriptionTitle =
                when (pageType) {
                    ReportMode.REPORT -> stringResource(R.string.report_description)
                    ReportMode.FEEDBACK -> stringResource(R.string.feedback_description)
                    ReportMode.FEATURE_REQUEST ->
                        stringResource(R.string.feature_request_description_title)
                }
            val descriptionPlaceholder =
                when (pageType) {
                    ReportMode.REPORT -> stringResource(R.string.please_fill_feedback_full)
                    ReportMode.FEEDBACK ->
                        stringResource(R.string.feedback_description_placeholder)
                    ReportMode.FEATURE_REQUEST ->
                        stringResource(R.string.feature_request_description_placeholder)
                }
            ReportDescriptionContainer(
                title = descriptionTitle,
                description = description,
                onDescriptionChange = onDescriptionChange,
                placeholder = descriptionPlaceholder,
            )

            Spacer(Modifier.height(24.dp))

            // 图片证据
            val imageSectionTitle =
                when (pageType) {
                    ReportMode.FEATURE_REQUEST ->
                        stringResource(R.string.feature_request_image_label)
                    else -> stringResource(R.string.image_evidence_full)
                }
            ReportImageEvidenceContainer(
                title = imageSectionTitle,
                images = images,
                onClickAddImage = onClickAddImage,
            )

            Spacer(Modifier.height(60.dp))

            SaveBtn(onSave = onSave, isSubmitting = isSubmitting)
            Spacer(Modifier.height(60.dp))
        }

        // 顶部导航栏
        CenterAlignedTopAppBar(
            colors =
                TopAppBarDefaults.centerAlignedTopAppBarColors()
                    .copy(containerColor = Color(0XFF1C1523)),
            title = {
                val appBarTitle =
                    when (pageType) {
                        ReportMode.REPORT -> stringResource(R.string.str_report)
                        ReportMode.FEEDBACK -> stringResource(R.string.share_feedback)
                        ReportMode.FEATURE_REQUEST ->
                            stringResource(R.string.feature_request_title)
                    }
                Text(
                    text = appBarTitle,
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 20.sp,
                )
            },
            navigationIcon = {
                Image(
                    modifier = Modifier.padding(horizontal = 12.dp).noRippleClickable { onBack() },
                    painter = painterResource(R.drawable.back),
                    contentDescription = null,
                )
            },
        )
    }
}

@Preview(showBackground = true)
@Composable
fun ReportScreenPreview() {
    val mockReasons =
        listOf(
            ReportItem(id = 1, description = "不当内容"),
            ReportItem(id = 2, description = "垃圾信息"),
            ReportItem(id = 3, description = "骚扰行为"),
        )

    ReportScreen(
        onBack = {},
        reasons = mockReasons,
        selectIDs = setOf(1),
        onClickReason = { _, _ -> },
        description = "这是一条举报描述",
        onDescriptionChange = {},
        images = listOf(),
        onClickAddImage = {},
        onSave = {},
    )
}
