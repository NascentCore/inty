package com.ai.intellimate.xb.navigation

import android.net.Uri

object RoutesMe {
    /** 设置页面路由 */
    const val Settings = "settings"

    /** VIP订阅中心页面路由 */
    const val VipCenter = "vip_center"

    /** 签到页面路由 */
    const val CheckIn = "check_in"

    /** 编辑个人资料页面路由 */
    const val ModifyProfile = "modify_profile"

    /** 管理订阅页面路由 */
    const val SubsManagement = "subs_management"

    private const val REPORT_DEFAULT_TARGET_TYPE = "USER"
    private const val REPORT_DEFAULT_TARGET_ID = "_" // 避免空 path segment 导致路由不匹配
    private const val REPORT_QUERY_PREFILL = "prefill"

    const val ReportPage =
        "report_page/{isFeedback}/{targetType}/{targetId}?$REPORT_QUERY_PREFILL={$REPORT_QUERY_PREFILL}"

    fun reportPage(
        isFeedback: Boolean,
        targetType: String = REPORT_DEFAULT_TARGET_TYPE,
        targetId: String = REPORT_DEFAULT_TARGET_ID,
        prefill: String = "",
    ): String {
        val encodedPrefill = Uri.encode(prefill)
        return "report_page/${isFeedback}/${targetType}/${targetId}?$REPORT_QUERY_PREFILL=$encodedPrefill"
    }
}
