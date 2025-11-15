package com.ai.intellimate.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.TextUnit
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatTextFormatterTest {
    @Test
    fun formatChatMessage_appliesItalicStyleWithinBrackets() {
        val input = "Hello (world)"
        val result =
            ChatTextFormatter.formatChatMessage(
                text = input,
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Normal,
                normalColor = Color.Black,
                italicColor = Color.Red,
            )

        // Text remains unchanged
        assertEquals(input, result.text)

        // Find span for the bracket content
        val italicSpan =
            result.spanStyles.find { span ->
                result.text.substring(span.start, span.end) == "world"
            }

        assertNotNull("Italic span for bracket content not found", italicSpan)
        assertEquals(FontStyle.Italic, italicSpan!!.item.fontStyle)
        assertEquals(Color.Red, italicSpan.item.color)
    }

    @Test
    fun formatChatMessage_handlesNestedEnglishAndChineseBrackets() {
        val input = "前缀 (outer （inner） text) 后缀"
        val result =
            ChatTextFormatter.formatChatMessage(
                text = input,
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Normal,
                normalColor = Color.Black,
                italicColor = Color.Blue,
            )

        val italicSegments =
            result.spanStyles
                .filter { it.item.fontStyle == FontStyle.Italic }
                .map { result.text.substring(it.start, it.end) }

        assertTrue(italicSegments.contains("outer （inner） text"))
        assertEquals(input, result.text)
    }

    @Test
    fun formatChatMessage_ignoresUnmatchedBracketsAndKeepsEmoji() {
        val input = "Hello 😀 (missing end"
        val result =
            ChatTextFormatter.formatChatMessage(
                text = input,
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Bold,
                normalColor = Color.Black,
                italicColor = Color.Green,
            )

        val containsItalic =
            result.spanStyles.any { span -> span.item.fontStyle == FontStyle.Italic }

        assertEquals(input, result.text)
        assertTrue("Unexpected italic span created for unmatched brackets", !containsItalic)
    }
}
