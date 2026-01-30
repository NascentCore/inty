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

/**
 * 使用 DSL 构建参数并上报事件。
 * 参数经 [FirebaseManager.safeEventParams] 校验：参数数量限制、key/value 规范化与截断。
 *
 * 使用示例:
 * ```kotlin
 * "purchase_complete".logEvent {
 *     put("item_id", "12345")
 *     put("currency", "CNY")
 * }
 * ```
 *
 * @param buildParams 在 [MutableMap] 上执行的 lambda，用于添加事件参数（key 为 String，value 为 Any?，null 会被转为 "unknown"）
 */
fun String.logEvent(buildParams: MutableMap<String, Any?>.() -> Unit) {
    val rawParams = mutableMapOf<String, Any?>().apply(buildParams)
    val params = FirebaseManager.safeEventParams(*rawParams.map { it.key to it.value }.toTypedArray())
    FirebaseManager.logEvent(this, params as Map<String, Any>)
}
