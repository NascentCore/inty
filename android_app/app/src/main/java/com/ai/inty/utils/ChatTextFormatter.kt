package com.ai.inty.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit

/**
 * 聊天文本格式化工具类
 * 将括号内容转换为斜体，支持嵌套括号
 */
object ChatTextFormatter {

    /**
     * 格式化聊天消息文本
     *
     * @param text 原始文本
     * @param fontSize 字体大小
     * @param fontWeight 字体粗细
     * @param normalColor 正常文本颜色
     * @param italicColor 斜体文本颜色
     * @return 格式化后的AnnotatedString
     */
    fun formatChatMessage(
        text: String,
        fontSize: TextUnit,
        fontWeight: FontWeight,
        normalColor: Color,
        italicColor: Color,
    ): AnnotatedString = buildAnnotatedString {
        val bracketPairs = findBracketPairs(text)
        var currentIndex = 0
        var pairIndex = 0

        while (currentIndex < text.length) {
            if (pairIndex < bracketPairs.size && currentIndex == bracketPairs[pairIndex].first) {
                // 开始括号 - 斜体样式
                withStyle(
                    SpanStyle(
                        color = italicColor,
                        fontSize = fontSize,
                        fontWeight = fontWeight,
                        fontStyle = FontStyle.Italic,
                        fontFamily = FontFamily.Default
                    )
                ) {
                    append(text[currentIndex])
                }
                currentIndex++

                // 括号内容为斜体
                val endIndex = bracketPairs[pairIndex].second
                withStyle(
                    SpanStyle(
                        color = italicColor,
                        fontSize = fontSize,
                        fontWeight = fontWeight,
                        fontStyle = FontStyle.Italic,
                        fontFamily = FontFamily.Default
                    )
                ) {
                    append(text.substring(currentIndex, endIndex))
                }

                // 结束括号 - 斜体样式
                withStyle(
                    SpanStyle(
                        color = italicColor,
                        fontSize = fontSize,
                        fontWeight = fontWeight,
                        fontStyle = FontStyle.Italic,
                        fontFamily = FontFamily.Default
                    )
                ) {
                    append(text[endIndex])
                }
                currentIndex = endIndex + 1
                pairIndex++
            } else {
                // 普通文本 - 按字符串片段添加而不是逐字符，避免破坏emoji
                val nextBracketIndex = if (pairIndex < bracketPairs.size) {
                    bracketPairs[pairIndex].first
                } else {
                    text.length
                }
                
                withStyle(
                    SpanStyle(
                        color = normalColor,
                        fontSize = fontSize,
                        fontWeight = fontWeight,
                        fontFamily = FontFamily.Default
                    )
                ) {
                    append(text.substring(currentIndex, nextBracketIndex))
                }
                currentIndex = nextBracketIndex
            }
        }
    }

    /**
     * 查找匹配的括号对
     */
    private fun findBracketPairs(text: String): List<Pair<Int, Int>> {
        val bracketPairs = mutableListOf<Pair<Int, Int>>()
        val stack = mutableListOf<Pair<Char, Int>>()

        text.forEachIndexed { index, char ->
            when (char) {
                '(', '（' -> stack.add(Pair(char, index))
                ')', '）' -> {
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