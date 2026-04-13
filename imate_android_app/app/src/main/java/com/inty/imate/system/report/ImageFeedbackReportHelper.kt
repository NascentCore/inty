package com.inty.imate.system.report

import com.inty.imate.system.report.data.ReportReasonCode

internal const val IMAGE_FEEDBACK_TARGET_PREFIX = "IMAGE_FEEDBACK_"
private const val IMAGE_FEEDBACK_MARKER = "[IMAGE_FEEDBACK]"
private const val IMAGE_FEEDBACK_REASON_CODES_MARKER_PREFIX = "[reason_codes="

internal val IMAGE_FEEDBACK_REASON_CODES: Set<ReportReasonCode> =
    setOf(
        ReportReasonCode.IMAGE_LOW_QUALITY,
        ReportReasonCode.IMAGE_STYLE_MISMATCH,
        ReportReasonCode.IMAGE_CONTENT_MISMATCH,
        ReportReasonCode.IMAGE_ANATOMY_OR_STRUCTURE_ERROR,
        ReportReasonCode.IMAGE_OTHER,
    )

internal fun buildImageFeedbackTargetId(imageUrl: String): String {
    return IMAGE_FEEDBACK_TARGET_PREFIX + fnv1aHashHex(imageUrl)
}

internal fun normalizeImageFeedbackVote(vote: String?): String? {
    return when (vote?.trim()?.lowercase()) {
        "like" -> "like"
        "dislike" -> "dislike"
        else -> null
    }
}

internal fun buildImageFeedbackDescription(userDescription: String, vote: String?): String {
    val normalizedVote = normalizeImageFeedbackVote(vote)
    val voteMarker = normalizedVote?.let { "[vote=$it]" }.orEmpty()
    return buildImageFeedbackDescriptionInternal(
        userDescription = userDescription,
        voteMarker = voteMarker,
        selectedReasonCodes = emptyList(),
    )
}

internal fun buildImageFeedbackDescription(
    userDescription: String,
    vote: String?,
    selectedReasonCodes: Collection<ReportReasonCode>,
): String {
    val normalizedVote = normalizeImageFeedbackVote(vote)
    val voteMarker = normalizedVote?.let { "[vote=$it]" }.orEmpty()
    return buildImageFeedbackDescriptionInternal(userDescription, voteMarker, selectedReasonCodes)
}

private fun buildImageFeedbackDescriptionInternal(
    userDescription: String,
    voteMarker: String,
    selectedReasonCodes: Collection<ReportReasonCode>,
): String {
    val reasonCodesMarker =
        selectedReasonCodes
            .asSequence()
            .map { it.name }
            .distinct()
            .toList()
            .takeIf { it.isNotEmpty() }
            ?.joinToString(separator = ",")
            ?.let { "$IMAGE_FEEDBACK_REASON_CODES_MARKER_PREFIX$it]" }
            .orEmpty()
    val descriptionPrefix = IMAGE_FEEDBACK_MARKER + voteMarker
    val trimmedUserDescription = userDescription.trim()
    return "$descriptionPrefix$reasonCodesMarker $trimmedUserDescription".trim()
}

private fun fnv1aHashHex(input: String): String {
    var hash = 0x811c9dc5.toInt()
    input.forEach { char ->
        hash = hash xor char.code
        hash *= 0x01000193
    }
    return hash.toUInt().toString(16).padStart(8, '0')
}
