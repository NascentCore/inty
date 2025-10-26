package ai.sxwl.android.common.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.withStyle

/** 文案解析工具类 用于解析opening文案中的括号内容，将括号内的文案设置为斜体和浅色 */
object TextParser {
    /**
     * 解析opening文案，将()内的内容设置为斜体和浅色
     *
     * @param text 原始文案
     * @return 解析后的AnnotatedString
     */
    fun parseOpeningText(text: String): AnnotatedString {
        return AnnotatedString.Builder()
            .apply {
                var currentIndex = 0
                var inParentheses = false
                var parenthesesStart = -1

                while (currentIndex < text.length) {
                    val char = text[currentIndex]

                    when {
                        char == '(' && !inParentheses -> {
                            // 开始括号
                            inParentheses = true
                            parenthesesStart = currentIndex
                            // 使用斜体和浅色样式渲染开始括号
                            withStyle(
                                style =
                                SpanStyle(
                                    fontStyle = FontStyle.Companion.Italic,
                                    color = Color(0x8CFFFFFF), // 浅色
                                ),
                            ) {
                                append(char.toString())
                            }
                        }
                        char == ')' && inParentheses -> {
                            // 结束括号
                            inParentheses = false
                            parenthesesStart = -1
                            // 使用斜体和浅色样式渲染结束括号
                            withStyle(
                                style =
                                SpanStyle(
                                    fontStyle = FontStyle.Companion.Italic,
                                    color = Color(0x8CFFFFFF), // 浅色
                                ),
                            ) {
                                append(char.toString())
                            }
                        }
                        inParentheses -> {
                            // 在括号内，使用斜体和浅色样式
                            withStyle(
                                style =
                                SpanStyle(
                                    fontStyle = FontStyle.Companion.Italic,
                                    color = Color(0x8CFFFFFF), // 浅色
                                ),
                            ) {
                                append(char.toString())
                            }
                        }
                        else -> {
                            // 正常文本
                            append(char.toString())
                        }
                    }
                    currentIndex++
                }
            }
            .toAnnotatedString()
    }

    /**
     * 检查文本是否包含括号
     *
     * @param text 文本内容
     * @return 是否包含括号
     */
    fun hasParentheses(text: String): Boolean {
        return text.contains("(") && text.contains(")")
    }

    /**
     * 提取括号内的内容
     *
     * @param text 文本内容
     * @return 括号内的内容列表
     */
    fun extractParenthesesContent(text: String): List<String> {
        val result = mutableListOf<String>()
        val regex = "\\((.*?)\\)".toRegex()

        regex.findAll(text).forEach { matchResult -> result.add(matchResult.groupValues[1]) }

        return result
    }
}
