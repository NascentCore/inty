package com.ai.intellimate.agent.report

import ai.sxwl.android.data.api.model.ReportItem

class ReportViewModel : BaseFeedbackViewModel() {

    override fun createReasonItems(): List<ReportItem> =
        listOf(
            ReportItem(
                id = 1,
                description = "Sensitive or sexual content",
                code = "SENSITIVE_CONTENT",
            ),
            ReportItem(id = 2, description = "Misinformation", code = "MISINFORMATION"),
            ReportItem(id = 3, description = "Fraud or scams", code = "FRAUD_SCAMS"),
            ReportItem(
                id = 4,
                description = "Violation of privacy",
                code = "PRIVACY_VIOLATION",
            ),
            ReportItem(id = 5, description = "Harmful to minors", code = "HARMFUL_MINORS"),
            ReportItem(
                id = 6,
                description = "Violations of my intellectual property",
                code = "IP_VIOLATION",
            ),
            ReportItem(
                id = 0,
                description = "Other, details in report description",
                code = "OTHER",
            ),
        )
}
