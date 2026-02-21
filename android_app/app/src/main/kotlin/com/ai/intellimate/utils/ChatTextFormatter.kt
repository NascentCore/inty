package com.ai.intellimate.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit

/** 聊天文本格式化工具类：将动作描述（括号或 *...*）转为斜体；括号与 * 二选一，由 [actionMarkerBrackets] 控制。 */
object ChatTextFormatter {

    private const val SINGLE_ASTERISK_LEN = 1

    /**
     * 格式化聊天消息文本。空字符串返回空 AnnotatedString。
     *
     * @param text 原始文本
     * @param fontSize 字体大小
     * @param fontWeight 字体粗细
     * @param normalColor 正常文本颜色
     * @param italicColor 斜体文本颜色（动作描述）
     * @param actionMarkerBrackets true 用 ()/（） 标记动作，false 用 *...* 标记
     * @return 格式化后的AnnotatedString
     */
    fun formatChatMessage(
        text: String,
        fontSize: TextUnit,
        fontWeight: FontWeight,
        normalColor: Color,
        italicColor: Color,
        actionMarkerBrackets: Boolean = true,
    ): AnnotatedString {
        val actionRanges =
            if (actionMarkerBrackets) findBracketPairs(text)
            else findSingleAsteriskPairs(text)
        val italicStyle =
            SpanStyle(
                color = italicColor,
                fontSize = fontSize,
                fontWeight = fontWeight,
                fontStyle = FontStyle.Italic,
                fontFamily = FontFamily.Default,
            )
        val normalStyle =
            SpanStyle(
                color = normalColor,
                fontSize = fontSize,
                fontWeight = fontWeight,
                fontFamily = FontFamily.Default,
            )
        return buildAnnotatedString {
            var currentIndex = 0
            var pairIndex = 0
            while (currentIndex < text.length) {
                if (pairIndex < actionRanges.size && currentIndex == actionRanges[pairIndex].first) {
                    val endIndex = actionRanges[pairIndex].second
                    withStyle(italicStyle) {
                        if (actionMarkerBrackets) {
                            if (endIndex < text.length) {
                                append(text.substring(currentIndex, endIndex + 1))
                            } else {
                                append(text.substring(currentIndex))
                            }
                        } else {
                            // *...* 模式：只追加中间内容，不显示 *
                            val innerStart = currentIndex + SINGLE_ASTERISK_LEN
                            val innerEndExclusive = endIndex
                            if (innerStart < innerEndExclusive) {
                                append(text.substring(innerStart, innerEndExclusive))
                            }
                        }
                    }
                    currentIndex = if (endIndex < text.length) endIndex + 1 else text.length
                    pairIndex++
                } else {
                    val nextStart =
                        if (pairIndex < actionRanges.size) actionRanges[pairIndex].first
                        else text.length
                    if (currentIndex < nextStart) {
                        withStyle(normalStyle) {
                            append(text.substring(currentIndex, nextStart))
                        }
                        currentIndex = nextStart
                    } else {
                        if (pairIndex < actionRanges.size) pairIndex++
                        else currentIndex = text.length
                    }
                }
            }
        }
    }

    /** 查找非重叠的 *...* 对（单个 * 包裹），返回 (start, end) 含首尾 * 的闭区间；** 不视为一对。 */
    private fun findSingleAsteriskPairs(text: String): List<Pair<Int, Int>> {
        val pairs = mutableListOf<Pair<Int, Int>>()
        var i = 0
        while (i < text.length) {
            if (text[i] == '*' && (i + 1 >= text.length || text[i + 1] != '*')) {
                var j = i + 1
                while (j < text.length) {
                    when {
                        text[j] == '*' && (j + 1 >= text.length || text[j + 1] != '*') -> {
                            pairs.add(Pair(i, j))
                            i = j + 1
                            break
                        }
                        text[j] == '*' && j + 1 < text.length && text[j + 1] == '*' -> j += 2
                        else -> j++
                    }
                }
                // 未找到配对闭合 * 时跳过该起始 *，避免重复匹配
                if (j >= text.length) i++
            } else if (text[i] == '*' && i + 1 < text.length && text[i + 1] == '*') {
                i += 2
            } else {
                i++
            }
        }
        return pairs
    }

    /** 查找匹配的括号对，返回 (start, end) 含括号的闭区间。 */
    private fun findBracketPairs(text: String): List<Pair<Int, Int>> {
        val bracketPairs = mutableListOf<Pair<Int, Int>>()
        val stack = mutableListOf<Pair<Char, Int>>()

        text.forEachIndexed { index, char ->
            when (char) {
                '(',
                '（' -> stack.add(Pair(char, index))
                ')',
                '）' -> {
                    val matchingStart = if (char == ')') '(' else '（'
                    for (i in stack.size - 1 downTo 0) {
                        if (stack[i].first == matchingStart) {
                            bracketPairs.add(Pair(stack[i].second, index))
                            stack.removeAt(i)
                            break
                        }
                    }
                }
            }
        }

        return bracketPairs.sortedBy { it.first }
    }
}
