package com.ai.intellimate.ui

import ai.sxwl.android.common.analytics.PageTrackingHelper
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect

/**
 * 页面级 Composable 基础框架组件。
 *
 * 封装页面通用逻辑，目前主要用于自动化页面浏览埋点。
 * 所有需要埋点的页面应使用此组件包裹，确保埋点数据的一致性和完整性。
 *
 * 功能特性:
 * - 页面进入时自动上报 page_view 事件
 * - 支持自定义埋点参数扩展
 * - 使用 LaunchedEffect(Unit) 确保仅在首次组合时触发一次
 *
 * 使用示例:
 * ```kotlin
 * @Composable
 * fun ChatScreen(agentId: String) {
 *     IntyPage(
 *         pageName = "chat_screen",
 *         params = mapOf("agent_id" to agentId)
 *     ) {
 *         // 页面实际内容
 *         ChatContent()
 *     }
 * }
 * ```
 *
 * @param pageName 页面名称标识，用于埋点区分不同页面，建议使用 snake_case 格式
 * @param params 附加埋点参数，用于传递页面相关的业务数据，如角色 ID、来源等
 * @param content 页面实际内容的 Composable lambda
 */
@Composable
fun IntyPage(
    pageName: String,
    params: Map<String, Any> = mapOf(),
    content: @Composable () -> Unit
) {
    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView(
            pageName = pageName,
            pageClass = "MainActivity",
            additionalParams = params
        )
    }

    content()
}