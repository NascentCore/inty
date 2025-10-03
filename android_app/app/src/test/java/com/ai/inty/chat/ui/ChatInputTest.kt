package com.ai.inty.chat.ui

import org.junit.Assert.*
import org.junit.Test

/** ChatInput 相关函数的测试 */
class ChatInputTest {

    @Test
    fun `insertParenthesesAtCursor should be callable`() {
        // Given
        var currentText = "hello world"
        var currentSelection = 5
        val onTextUpdate: (String) -> Unit = { currentText = it }
        val onSelectionUpdate: (Int) -> Unit = { currentSelection = it }

        // When
        insertParenthesesAtCursor(
            currentText = currentText,
            currentSelection = currentSelection,
            onTextUpdate = onTextUpdate,
            onSelectionUpdate = onSelectionUpdate,
        )

        // Then
        assertNotNull("Function should execute without error", currentText)
        assertTrue("Text should be modified", currentText != "hello world")
    }

    @Test
    fun `insertParenthesesAtCursor should handle empty text`() {
        // Given
        var currentText = ""
        var currentSelection = 0
        val onTextUpdate: (String) -> Unit = { currentText = it }
        val onSelectionUpdate: (Int) -> Unit = { currentSelection = it }

        // When
        insertParenthesesAtCursor(
            currentText = currentText,
            currentSelection = currentSelection,
            onTextUpdate = onTextUpdate,
            onSelectionUpdate = onSelectionUpdate,
        )

        // Then
        assertNotNull("Function should execute without error", currentText)
        assertTrue("Text should contain parentheses", currentText.contains("()"))
    }

    @Test
    fun `isCursorInsideParentheses should return true when cursor is inside parentheses`() {
        // Test cases for isCursorInsideParentheses
        assertTrue(isCursorInsideParentheses("hello () world", 7))
        assertTrue(isCursorInsideParentheses("hello (text) world", 11))
        assertTrue(isCursorInsideParentheses("hello (text) world", 7))
        assertTrue(isCursorInsideParentheses("hello (()) world", 8))
    }

    @Test
    fun `isCursorInsideParentheses should return false when cursor is outside parentheses`() {
        // Test cases for isCursorInsideParentheses
        assertFalse(isCursorInsideParentheses("hello | world", 6))
        assertFalse(isCursorInsideParentheses("hello () | world", 9))
        assertFalse(isCursorInsideParentheses("hello (text) | world", 13))
        assertFalse(isCursorInsideParentheses("", 0))
        assertFalse(isCursorInsideParentheses("hello world", 5))
    }

    @Test
    fun `isCursorInsideParentheses should handle edge cases`() {
        // Test edge cases
        assertFalse(isCursorInsideParentheses("hello (", 7)) // 只有开括号
        assertFalse(isCursorInsideParentheses("hello )", 7)) // 只有闭括号
        assertFalse(isCursorInsideParentheses("hello (text", 7)) // 没有闭括号
        assertFalse(isCursorInsideParentheses("hello text)", 7)) // 没有开括号
    }
}
