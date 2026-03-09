package com.ai.intellimate.agent.report

internal const val IMAGE_FEEDBACK_TARGET_PREFIX = "IMAGE_FEEDBACK_"
private const val IMAGE_FEEDBACK_MARKER = "[IMAGE_FEEDBACK]"

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
    val descriptionPrefix = IMAGE_FEEDBACK_MARKER + voteMarker
    val trimmedUserDescription = userDescription.trim()
    return "$descriptionPrefix $trimmedUserDescription".trim()
}

private fun fnv1aHashHex(input: String): String {
    var hash = 0x811c9dc5.toInt()
    input.forEach { char ->
        hash = hash xor char.code
        hash *= 0x01000193
    }
    return hash.toUInt().toString(16).padStart(8, '0')
}
