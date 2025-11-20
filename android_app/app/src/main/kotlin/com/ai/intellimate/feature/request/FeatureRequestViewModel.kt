package com.ai.intellimate.feature.request

import ai.sxwl.android.data.api.model.ReportItem
import com.ai.intellimate.agent.report.BaseFeedbackViewModel

/**
 * Feature Request 提交 ViewModel
 */
class FeatureRequestViewModel : BaseFeedbackViewModel() {

    override fun createReasonItems(): List<ReportItem> =
        listOf(
            ReportItem(
                id = 101,
                description = "New AI character idea",
                code = "NEW_CHARACTER",
            ),
            ReportItem(
                id = 102,
                description = "Chat experience improvement",
                code = "CHAT_IMPROVEMENT",
            ),
            ReportItem(
                id = 103,
                description = "UI or accessibility improvement",
                code = "UI_IMPROVEMENT",
            ),
            ReportItem(
                id = 104,
                description = "Bug fix or stability request",
                code = "BUG_FIX",
            ),
            ReportItem(
                id = 199,
                description = "Other ideas (describe below)",
                code = "OTHER",
            ),
        )
}
