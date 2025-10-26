package ai.sxwl.android.utils

import java.io.UnsupportedEncodingException
import java.net.URLDecoder
import java.net.URLEncoder
import java.util.Base64

/** 编码工具类 提供编码相关的工具方法 */
object EncodeUtils {

    /** URL编码 */
    fun urlEncode(input: String?): String = urlEncode(input, "UTF-8")

    /** URL编码 */
    fun urlEncode(input: String?, charsetName: String): String {
        if (input.isNullOrEmpty()) return ""
        return try {
            URLEncoder.encode(input, charsetName)
        } catch (e: UnsupportedEncodingException) {
            // 使用UTF-8作为降级方案
            try {
                URLEncoder.encode(input, "UTF-8")
            } catch (e2: UnsupportedEncodingException) {
                // 如果UTF-8也不支持，返回原始字符串
                input
            }
        }
    }

    /** URL解码 */
    fun urlDecode(input: String?): String = urlDecode(input, "UTF-8")

    /** URL解码 */
    fun urlDecode(input: String?, charsetName: String): String {
        if (input.isNullOrEmpty()) return ""

        // 安全处理输入字符串，避免正则表达式异常
        val safeInput =
            try {
                input
                    .replace("%(?![0-9a-fA-F]{2})".toRegex(), "%25")
                    .replace("\\+".toRegex(), "%2B")
            } catch (e: Exception) {
                // 如果正则处理失败，直接使用原始输入
                input
            }

        return try {
            URLDecoder.decode(safeInput, charsetName)
        } catch (e: UnsupportedEncodingException) {
            // 使用UTF-8作为降级方案
            try {
                URLDecoder.decode(safeInput, "UTF-8")
            } catch (e2: UnsupportedEncodingException) {
                // 如果UTF-8也不支持，返回原始字符串
                input
            }
        }
    }

    /** Base64编码 */
    fun base64Encode(input: String?): ByteArray = base64Encode(input?.toByteArray())

    /** Base64编码 */
    fun base64Encode(input: ByteArray?): ByteArray {
        if (input == null || input.isEmpty()) return ByteArray(0)
        return Base64.getEncoder().encode(input)
    }

    /** Base64编码为字符串 */
    fun base64Encode2String(input: String?): String = base64Encode2String(input?.toByteArray())

    /** Base64编码为字符串 */
    fun base64Encode2String(input: ByteArray?): String {
        if (input == null || input.isEmpty()) return ""
        return Base64.getEncoder().encodeToString(input)
    }

    /** Base64解码 */
    fun base64Decode(input: String?): ByteArray {
        if (input == null || input.isEmpty()) return ByteArray(0)
        return try {
            Base64.getDecoder().decode(input)
        } catch (e: IllegalArgumentException) {
            // Base64格式错误，返回空数组
            ByteArray(0)
        } catch (e: Exception) {
            // 其他异常，返回空数组
            ByteArray(0)
        }
    }

    /** Base64解码 */
    fun base64Decode(input: ByteArray?): ByteArray {
        if (input == null || input.isEmpty()) return ByteArray(0)
        return try {
            Base64.getDecoder().decode(input)
        } catch (e: IllegalArgumentException) {
            // Base64格式错误，返回空数组
            ByteArray(0)
        } catch (e: Exception) {
            // 其他异常，返回空数组
            ByteArray(0)
        }
    }

    /** HTML编码 注意：此方法在JVM环境中使用简单的HTML转义 */
    fun htmlEncode(input: String?): String {
        if (input.isNullOrEmpty()) return ""
        return input
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
            .replace("'", "&#39;")
    }

    /** HTML解码 注意：此方法在JVM环境中使用简单的HTML解码 */
    fun htmlDecode(input: String?): String {
        if (input.isNullOrEmpty()) return ""
        return input
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
    }
}
