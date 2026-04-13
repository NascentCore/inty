package com.inty.imate.system.report.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
enum class ReportReasonCode {
    @SerialName("SENSITIVE_CONTENT") SENSITIVE_CONTENT,
    @SerialName("MISINFORMATION") MISINFORMATION,
    @SerialName("FRAUD_SCAMS") FRAUD_SCAMS,
    @SerialName("PRIVACY_VIOLATION") PRIVACY_VIOLATION,
    @SerialName("HARMFUL_MINORS") HARMFUL_MINORS,
    @SerialName("IP_VIOLATION") IP_VIOLATION,
    @SerialName("OTHER") OTHER,
    @SerialName("CHAT_NOT_NATURAL") CHAT_NOT_NATURAL,
    @SerialName("CHARACTER_MISMATCH") CHARACTER_MISMATCH,
    @SerialName("APP_SLOW") APP_SLOW,
    @SerialName("FEATURE_HARD_TO_FIND") FEATURE_HARD_TO_FIND,
    @SerialName("UI_INCONVENIENT") UI_INCONVENIENT,
    @SerialName("NEW_FEATURE") NEW_FEATURE,
    @SerialName("IMAGE_LOW_QUALITY") IMAGE_LOW_QUALITY,
    @SerialName("IMAGE_STYLE_MISMATCH") IMAGE_STYLE_MISMATCH,
    @SerialName("IMAGE_CONTENT_MISMATCH") IMAGE_CONTENT_MISMATCH,
    @SerialName("IMAGE_ANATOMY_OR_STRUCTURE_ERROR") IMAGE_ANATOMY_OR_STRUCTURE_ERROR,
    @SerialName("IMAGE_OTHER") IMAGE_OTHER,
}

@Serializable
enum class ReportTargetType {
    @SerialName("USER") USER,
    @SerialName("AGENT") AGENT,
}

@Serializable
enum class ReportRequestType {
    @SerialName("REPORT") REPORT,
    @SerialName("FEEDBACK") FEEDBACK,
}

@Serializable
data class ReportCreateRequest(
    @SerialName("target_id") val targetId: String,
    @SerialName("target_type") val targetType: ReportTargetType,
    @SerialName("reason_codes") val reasonCodes: List<ReportReasonCode>,
    val description: String,
    @SerialName("image_urls") val imageUrls: List<String> = emptyList(),
    @SerialName("report_type") val reportType: ReportRequestType = ReportRequestType.REPORT,
)

@Serializable
data class UploadAvatarResponse(
    @SerialName("url") val url: String = "",
    @SerialName("avatar_url") val avatarUrl: String = "",
)
