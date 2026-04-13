package com.inty.imate.system

data class SystemReportEntry(
    val isFeedback: Boolean,
    val targetType: String = "AGENT",
    val targetId: String = "",
    val initialEvidenceImageUrl: String = "",
    val imageFeedbackVote: String? = null,
)
