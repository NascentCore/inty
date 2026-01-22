package ai.sxwl.android.firebase

/**
 * Firebase Analytics 事件埋点扩展函数。
 *
 * 将字符串作为事件名称，便捷地上报 Firebase Analytics 事件。 内部调用 [FirebaseManager] 进行安全的参数处理和事件发送。
 *
 * 使用示例:
 * ```kotlin
 * // 无参数事件
 * "button_click".logEvent()
 *
 * // 带参数事件
 * "purchase_complete".logEvent(
 *     "item_id" to "12345",
 *     "price" to 99.99,
 *     "currency" to "CNY"
 * )
 * ```
 *
 * @param params 事件参数键值对，值支持 String、Int、Long、Double 等基础类型， null 值会被
 *   [FirebaseManager.safeEventParams] 安全过滤
 * @receiver 事件名称，建议使用 snake_case 格式，如 "screen_view"、"button_click"
 */
fun String.logEvent(vararg params: Pair<String, Any?>) {
    FirebaseManager.logEvent(this, FirebaseManager.safeEventParams(*params))
}
