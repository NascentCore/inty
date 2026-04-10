package com.ai.imate.system.report

import com.ai.intellimate.R
import com.ai.imate.system.report.data.ReportReasonCode

object ReportReasonMappings {
    val REPORT_REASON_CODE_TO_STRING_RES: Map<ReportReasonCode, Int> =
        mapOf(
            ReportReasonCode.SENSITIVE_CONTENT to R.string.system_report_reason_sensitive_content,
            ReportReasonCode.MISINFORMATION to R.string.system_report_reason_misinformation,
            ReportReasonCode.FRAUD_SCAMS to R.string.system_report_reason_fraud_scams,
            ReportReasonCode.PRIVACY_VIOLATION to R.string.system_report_reason_privacy_violation,
            ReportReasonCode.HARMFUL_MINORS to R.string.system_report_reason_harmful_minors,
            ReportReasonCode.IP_VIOLATION to R.string.system_report_reason_ip_violation,
            ReportReasonCode.OTHER to R.string.system_report_reason_other,
        )

    val FEEDBACK_REASON_CODE_TO_STRING_RES: Map<ReportReasonCode, Int> =
        mapOf(
            ReportReasonCode.CHAT_NOT_NATURAL to R.string.system_feedback_reason_chat_not_natural,
            ReportReasonCode.CHARACTER_MISMATCH to R.string.system_feedback_reason_character_mismatch,
            ReportReasonCode.APP_SLOW to R.string.system_feedback_reason_app_slow,
            ReportReasonCode.FEATURE_HARD_TO_FIND to R.string.system_feedback_reason_feature_hard_to_find,
            ReportReasonCode.UI_INCONVENIENT to R.string.system_feedback_reason_ui_inconvenient,
            ReportReasonCode.NEW_FEATURE to R.string.system_feedback_reason_new_feature,
            ReportReasonCode.OTHER to R.string.system_feedback_reason_other,
        )

    val IMAGE_FEEDBACK_REASON_CODE_TO_STRING_RES: Map<ReportReasonCode, Int> =
        mapOf(
            ReportReasonCode.IMAGE_LOW_QUALITY to R.string.system_feedback_reason_image_low_quality,
            ReportReasonCode.IMAGE_STYLE_MISMATCH to R.string.system_feedback_reason_image_style_mismatch,
            ReportReasonCode.IMAGE_CONTENT_MISMATCH to R.string.system_feedback_reason_image_content_mismatch,
            ReportReasonCode.IMAGE_ANATOMY_OR_STRUCTURE_ERROR to
                R.string.system_feedback_reason_image_anatomy_or_structure_error,
            ReportReasonCode.IMAGE_OTHER to R.string.system_feedback_reason_image_other,
        )
}
