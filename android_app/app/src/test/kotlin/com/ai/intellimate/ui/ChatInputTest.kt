package com.ai.intellimate.ui

import com.ai.intellimate.chat.ui.insertParenthesesAtCursor
import com.ai.intellimate.chat.ui.isCursorInsideParentheses
import org.junit.Assert
import org.junit.Test

/** ChatInput相关函数的测试 */
class ChatInputTest {

    @Test
    fun `insertParenthesesAtCursor should be callable`() {
// 给定
        var currentText = "hello world"
        var currentSelection = 5
        val onTextUpdate: (String) -> Unit = { currentText = it }
        val onSelectionUpdate: (Int) -> Unit = { currentSelection = it }
// 什么时候
        insertParenthesesAtCursor(
            currentText = currentText,
            currentSelection = currentSelection,
            onTextUpdate = onTextUpdate,
            onSelectionUpdate = onSelectionUpdate,
        )
// 然后
        Assert.assertNotNull("Function should execute without error", currentText)
        Assert.assertTrue("Text should be modified", currentText != "hello world")
    }

    @Test
    fun `insertParenthesesAtCursor should handle empty text`() {
// 给定
        var currentText = ""
        var currentSelection = 0
        val onTextUpdate: (String) -> Unit = { currentText = it }
        val onSelectionUpdate: (Int) -> Unit = { currentSelection = it }
// 什么时候
        insertParenthesesAtCursor(
            currentText = currentText,
            currentSelection = currentSelection,
            onTextUpdate = onTextUpdate,
            onSelectionUpdate = onSelectionUpdate,
        )
// 然后
        Assert.assertNotNull("Function should execute without error", currentText)
        Assert.assertTrue("Text should contain parentheses", currentText.contains("()"))
    }

    @Test
    fun `isCursorInsideParentheses should return true when cursor is inside parentheses`() {
// isCursorInsideParentheses 的测试示例
        Assert.assertTrue(isCursorInsideParentheses("hello () world", 7))
        Assert.assertTrue(isCursorInsideParentheses("hello (text) world", 11))
        Assert.assertTrue(isCursorInsideParentheses("hello (text) world", 7))
        Assert.assertTrue(isCursorInsideParentheses("hello (()) world", 8))
    }

    @Test
    fun `isCursorInsideParentheses should return false when cursor is outside parentheses`() {
// isCursorInsideParentheses 的测试示例
        Assert.assertFalse(isCursorInsideParentheses("hello | world", 6))
        Assert.assertFalse(isCursorInsideParentheses("hello () | world", 9))
        Assert.assertFalse(isCursorInsideParentheses("hello (text) | world", 13))
        Assert.assertFalse(isCursorInsideParentheses("", 0))
        Assert.assertFalse(isCursorInsideParentheses("hello world", 5))
    }

    @Test
    fun `isCursorInsideParentheses should handle edge cases`() {
// 测试边缘情况
        Assert.assertFalse(isCursorInsideParentheses("hello (", 7)) // 只有开括号
        Assert.assertFalse(isCursorInsideParentheses("hello )", 7)) // 只有闭括号
        Assert.assertFalse(isCursorInsideParentheses("hello (text", 7)) // 没有闭括号
        Assert.assertFalse(isCursorInsideParentheses("hello text)", 7)) // 没有开括号
    }
}
