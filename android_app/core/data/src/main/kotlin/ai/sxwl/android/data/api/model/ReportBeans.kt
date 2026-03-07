package ai.sxwl.android.data.api.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

enum class ReportReasonCode {
    @Json(name = "SENSITIVE_CONTENT") SENSITIVE_CONTENT,
    @Json(name = "MISINFORMATION") MISINFORMATION,
    @Json(name = "FRAUD_SCAMS") FRAUD_SCAMS,
    @Json(name = "PRIVACY_VIOLATION") PRIVACY_VIOLATION,
    @Json(name = "HARMFUL_MINORS") HARMFUL_MINORS,
    @Json(name = "IP_VIOLATION") IP_VIOLATION,
    @Json(name = "OTHER") OTHER,
    @Json(name = "CHAT_NOT_NATURAL") CHAT_NOT_NATURAL,
    @Json(name = "CHARACTER_MISMATCH") CHARACTER_MISMATCH,
    @Json(name = "APP_SLOW") APP_SLOW,
    @Json(name = "FEATURE_HARD_TO_FIND") FEATURE_HARD_TO_FIND,
    @Json(name = "UI_INCONVENIENT") UI_INCONVENIENT,
    @Json(name = "NEW_FEATURE") NEW_FEATURE,
}

enum class ReportTargetType {
    @Json(name = "USER") USER,
    @Json(name = "AGENT") AGENT,
}

enum class ReportRequestType {
    @Json(name = "REPORT") REPORT,
    @Json(name = "FEEDBACK") FEEDBACK,
}

@JsonClass(generateAdapter = true)
data class ReportCreateRequest(
    @Json(name = "target_id") val targetId: String,
    @Json(name = "target_type") val targetType: ReportTargetType,
    @Json(name = "reason_codes") val reasonCodes: List<ReportReasonCode>,
    val description: String,
    @Json(name = "image_urls") val imageUrls: List<String> = emptyList(),
    @Json(name = "report_type") val reportType: ReportRequestType = ReportRequestType.REPORT,
)

@JsonClass(generateAdapter = true)
data class ReportCreateApiResponse(val code: Int? = null, val message: String? = null)
