package com.ai.core.utils

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.core.content.getSystemService

/**
 * 剪贴板工具类
 *
 * 提供复制文本到剪贴板的功能
 *
 * 使用示例：
 *
 * ```kotlin
 * ClipboardUtils.copyToClipboard(context, "标签", "要复制的文本")
 * ```
 */
object ClipboardUtils {
    /**
     * 复制文本到剪贴板
     *
     * @param context 上下文
     * @param label 剪贴板标签
     * @param text 要复制的文本
     * @return 是否复制成功
     */
    fun copyToClipboard(context: Context, label: String, text: String): Boolean {
        if (text.isBlank()) {
            return false
        }
        val clipboard = context.getSystemService<ClipboardManager>() ?: return false
        val clip = ClipData.newPlainText(label, text)
        clipboard.setPrimaryClip(clip)
        return true
    }
}
