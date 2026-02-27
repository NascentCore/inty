package com.ai.intellimate.agent.report

import com.ai.intellimate.R
import ai.sxwl.android.data.api.model.ReportReasonCode

/**
 * 举报和反馈原因代码到字符串资源ID的映射
 *
 * 提供从 Inty SDK 的 ReasonCode 到 strings.xml 中字符串资源ID的完整映射
 * * 来自：app/schemas/report.py，经 OpenAPI 生成 inty sdk
 */
object ReportReasonMappings {

    /**
     * 举报原因代码到字符串资源ID的映射（常量，不可变） 映射 SDK 的 ReasonCode 到 strings.xml 中的资源ID 后端更新新的 code 之后这里需要更新
     *
     * 注意：使用 val 而非 const val，因为 const val 仅支持基本类型和 String，不支持 Map 类型
     */
    val REPORT_REASON_CODE_TO_STRING_RES: Map<ReportReasonCode, Int> =
        mapOf(
            ReportReasonCode.SENSITIVE_CONTENT to R.string.report_reason_sensitive_content,
            ReportReasonCode.MISINFORMATION to R.string.report_reason_misinformation,
            ReportReasonCode.FRAUD_SCAMS to R.string.report_reason_fraud_scams,
            ReportReasonCode.PRIVACY_VIOLATION to R.string.report_reason_privacy_violation,
            ReportReasonCode.HARMFUL_MINORS to R.string.report_reason_harmful_minors,
            ReportReasonCode.IP_VIOLATION to R.string.report_reason_ip_violation,
            ReportReasonCode.OTHER to R.string.report_reason_other,
        )

    /**
     * 反馈原因代码到字符串资源ID的映射（常量，不可变） 映射 SDK 的 ReasonCode 到 strings.xml 中的资源ID 后端更新新的 code 之后这里需要更新
     *
     * 注意：使用 val 而非 const val，因为 const val 仅支持基本类型和 String，不支持 Map 类型
     */
    val FEEDBACK_REASON_CODE_TO_STRING_RES: Map<ReportReasonCode, Int> =
        mapOf(
            ReportReasonCode.CHAT_NOT_NATURAL to R.string.feedback_reason_chat_not_natural,
            ReportReasonCode.CHARACTER_MISMATCH to R.string.feedback_reason_character_mismatch,
            ReportReasonCode.APP_SLOW to R.string.feedback_reason_app_slow,
            ReportReasonCode.FEATURE_HARD_TO_FIND to R.string.feedback_reason_feature_hard_to_find,
            ReportReasonCode.UI_INCONVENIENT to R.string.feedback_reason_ui_inconvenient,
            ReportReasonCode.NEW_FEATURE to R.string.feedback_reason_new_feature,
            ReportReasonCode.OTHER to R.string.feedback_reason_other,
        )
}
