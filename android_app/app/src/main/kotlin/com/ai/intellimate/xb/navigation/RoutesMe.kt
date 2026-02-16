package com.ai.intellimate.xb.navigation

object RoutesMe {
    /** 设置页面路由 */
    const val Settings = "settings"

    /** VIP订阅中心页面路由 */
    const val VipCenter = "vip_center?pageSource={pageSource}"

    /** 签到页面路由 */
    const val CheckIn = "check_in"

    /** 编辑个人资料页面路由 */
    const val ModifyProfile = "modify_profile"

    /** 管理订阅页面路由 */
    const val SubsManagement = "subs_management"

    const val ReportPage = "report_page/{isFeedback}/{targetType}/{targetId}"
    const val ReportInitialEvidenceImageUrlKey = "report_initial_evidence_image_url"

    fun vipCenter(pageSource: String) = "vip_center?pageSource=${pageSource}"

    fun reportPage(isFeedback: Boolean, targetType: String = "USER", targetId: String = "") =
        "report_page/${isFeedback}/${targetType}/${targetId}"
}
