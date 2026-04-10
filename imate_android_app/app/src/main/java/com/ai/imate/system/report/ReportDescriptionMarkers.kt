package com.ai.imate.system.report

private const val REPORT_DESCRIPTION_APP_VERSION_MARKER = "[INTY_APP_VERSION]"
private const val REPORT_DESCRIPTION_AGENT_ID_MARKER = "[INTY_AGENT_ID]"

internal fun buildReportDescriptionWithAppVersion(
    userDescription: String,
    versionName: String,
    versionCode: Int,
    agentId: String,
): String {
    val normalizedAgentId = agentId.trim()
    val hasAppVersionMarker = userDescription.contains(REPORT_DESCRIPTION_APP_VERSION_MARKER)
    val hasAgentIdMarker = userDescription.contains(REPORT_DESCRIPTION_AGENT_ID_MARKER)
    if (hasAppVersionMarker && (normalizedAgentId.isEmpty() || hasAgentIdMarker)) {
        return userDescription
    }
    val suffix = buildString {
        if (!hasAppVersionMarker) {
            append("--- ")
            append(REPORT_DESCRIPTION_APP_VERSION_MARKER)
            append(" ---")
            append('\n')
            append("App version: ")
            append(versionName)
            append(" (")
            append(versionCode)
            append(')')
        }
        if (normalizedAgentId.isNotEmpty() && !hasAgentIdMarker) {
            if (isNotEmpty()) {
                append('\n')
            }
            append("--- ")
            append(REPORT_DESCRIPTION_AGENT_ID_MARKER)
            append(" ---")
            append('\n')
            append("Agent ID: ")
            append(normalizedAgentId)
        }
    }
    if (suffix.isEmpty()) return userDescription
    val separator = if (userDescription.endsWith("\n")) "\n" else "\n\n"
    return userDescription + separator + suffix
}

internal fun mergeEvidenceImageUrls(
    remoteImages: Collection<String>,
    localImages: Collection<String>,
): List<String> {
    val merged = LinkedHashSet<String>()
    remoteImages.asSequence().map { it.trim() }.filter { it.isNotEmpty() }.forEach { merged.add(it) }
    localImages.asSequence().map { it.trim() }.filter { it.isNotEmpty() }.forEach { merged.add(it) }
    return merged.toList()
}
