// CREATED_BY_AGENT
package com.ai.intellimate.utils

import android.content.Context
import ai.sxwl.android.common.utils.HeartAppUtils

private const val DEFAULT_DISPLAY_ID_VISIBLE_LENGTH = 8

/**
 * 将长 ID 格式化为仅显示尾部若干位，默认保留 8 位，便于 UI 排版。
 * 在 debug 模式下，如果提供了 context，将显示完整 ID。
 *
 * @param fullId 原始完整 ID
 * @param visibleLength 希望展示的尾部长度，默认为 8
 * @param context 可选的 Context，用于判断是否是 debug 模式
 * @return 根据规则截取后的 ID，可直接用作 UI 展示
 */
fun formatDisplayId(
    fullId: String,
    visibleLength: Int = DEFAULT_DISPLAY_ID_VISIBLE_LENGTH,
    context: Context? = null,
): String {
    if (fullId.isEmpty()) {
        return fullId
    }
    // 在 debug 模式下，如果提供了 context，显示完整 ID
    if (context != null && HeartAppUtils.isAppDebugMode(context)) {
        return fullId
    }
    if (visibleLength <= 0 || fullId.length <= visibleLength) {
        return fullId
    }
    return fullId.takeLast(visibleLength)
}
