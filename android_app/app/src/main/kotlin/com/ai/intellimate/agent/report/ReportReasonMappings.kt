package com.ai.intellimate.agent.report

import com.ai.intellimate.R
import com.inty.api.models.api.v1.report.ReportCreateParams

/**
 * 举报和反馈原因代码到字符串资源ID的映射
 * 
 * 提供从 Inty SDK 的 ReasonCode 到 strings.xml 中字符串资源ID的完整映射
 */
object ReportReasonMappings {

    /**
     * 举报原因代码到字符串资源ID的映射
     * 映射 SDK 的 ReasonCode 到 strings.xml 中的资源ID
     * 后端更新新的 code 之后这里需要更新
     */
    val REPORT_REASON_CODE_TO_STRING_RES: Map<ReportCreateParams.ReasonCode, Int> =
        mapOf(
            ReportCreateParams.ReasonCode.SENSITIVE_CONTENT to R.string.report_reason_sensitive_content,
            ReportCreateParams.ReasonCode.MISINFORMATION to R.string.report_reason_misinformation,
            ReportCreateParams.ReasonCode.FRAUD_SCAMS to R.string.report_reason_fraud_scams,
            ReportCreateParams.ReasonCode.PRIVACY_VIOLATION to R.string.report_reason_privacy_violation,
            ReportCreateParams.ReasonCode.HARMFUL_MINORS to R.string.report_reason_harmful_minors,
            ReportCreateParams.ReasonCode.IP_VIOLATION to R.string.report_reason_ip_violation,
            ReportCreateParams.ReasonCode.OTHER to R.string.report_reason_other,
        )

    /**
     * 反馈原因代码到字符串资源ID的映射
     * 映射 SDK 的 ReasonCode 到 strings.xml 中的资源ID
     * 后端更新新的 code 之后这里需要更新
     */
    val FEEDBACK_REASON_CODE_TO_STRING_RES: Map<ReportCreateParams.ReasonCode, Int> =
        mapOf(
            ReportCreateParams.ReasonCode.CHAT_NOT_NATURAL to R.string.feedback_reason_chat_not_natural,
            ReportCreateParams.ReasonCode.CHARACTER_MISMATCH to R.string.feedback_reason_character_mismatch,
            ReportCreateParams.ReasonCode.APP_SLOW to R.string.feedback_reason_app_slow,
            ReportCreateParams.ReasonCode.FEATURE_HARD_TO_FIND to R.string.feedback_reason_feature_hard_to_find,
            ReportCreateParams.ReasonCode.UI_INCONVENIENT to R.string.feedback_reason_ui_inconvenient,
            ReportCreateParams.ReasonCode.NEW_FEATURE to R.string.feedback_reason_new_feature,
            ReportCreateParams.ReasonCode.OTHER to R.string.feedback_reason_other,
        )
}

