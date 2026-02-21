package com.ai.intellimate.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.TextUnit
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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

        // Find span for the bracket content (formatter styles the full segment including parentheses)
        val italicSpan =
            result.spanStyles.find { span ->
                result.text.substring(span.start, span.end) == "(world)"
            }

        assertNotNull("Italic span for bracket content not found", italicSpan)
        assertEquals(FontStyle.Italic, italicSpan!!.item.fontStyle)
        assertEquals(Color.Red, italicSpan.item.color)
    }

    @Test
    fun formatChatMessage_withSingleAsterisk_appliesItalicStyleAndHidesAsterisks() {
        val input = "Hello *world*"
        val result =
            ChatTextFormatter.formatChatMessage(
                text = input,
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Normal,
                normalColor = Color.Black,
                italicColor = Color.Red,
                actionMarkerBrackets = false,
            )

        // * 不显示，只显示中间内容
        assertEquals("Hello world", result.text)

        val italicSpan =
            result.spanStyles.find { span ->
                result.text.substring(span.start, span.end) == "world"
            }
        assertNotNull("Italic span for * segment not found", italicSpan)
        assertEquals(FontStyle.Italic, italicSpan!!.item.fontStyle)
        assertEquals(Color.Red, italicSpan.item.color)
    }

    @Test
    fun formatChatMessage_bracketMode_doesNotStyleSingleAsterisk() {
        val input = "Hello *world*"
        val result =
            ChatTextFormatter.formatChatMessage(
                text = input,
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Normal,
                normalColor = Color.Black,
                italicColor = Color.Red,
                actionMarkerBrackets = true,
            )

        assertEquals(input, result.text)
        val hasItalicSpan =
            result.spanStyles.any { it.item.fontStyle == FontStyle.Italic }
        assertFalse("Bracket mode must not style * as action", hasItalicSpan)
    }

    @Test
    fun formatChatMessage_singleAsterisk_twoSegments() {
        val input = "*a* *b*"
        val result =
            ChatTextFormatter.formatChatMessage(
                text = input,
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Normal,
                normalColor = Color.Black,
                italicColor = Color.Red,
                actionMarkerBrackets = false,
            )

        // * 不显示
        assertEquals("a b", result.text)
        val italicSpans =
            result.spanStyles.filter { it.item.fontStyle == FontStyle.Italic }
        assertTrue(italicSpans.size >= 2)
        val segments =
            italicSpans.map { result.text.substring(it.start, it.end) }
        assertTrue(segments.contains("a"))
        assertTrue(segments.contains("b"))
    }

    @Test
    fun formatChatMessage_asteriskMode_doubleAsteriskNotMatchedAsAction() {
        val input = "**bold**"
        val result =
            ChatTextFormatter.formatChatMessage(
                text = input,
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Normal,
                normalColor = Color.Black,
                italicColor = Color.Red,
                actionMarkerBrackets = false,
            )
        assertEquals(input, result.text)
        val hasItalicSpan =
            result.spanStyles.any { it.item.fontStyle == FontStyle.Italic }
        assertFalse("** must not be treated as single-asterisk action pair", hasItalicSpan)
    }

    @Test
    fun formatChatMessage_emptyString_returnsEmptyAnnotatedString() {
        val result =
            ChatTextFormatter.formatChatMessage(
                text = "",
                fontSize = TextUnit.Unspecified,
                fontWeight = FontWeight.Normal,
                normalColor = Color.Black,
                italicColor = Color.Red,
                actionMarkerBrackets = true,
            )
        assertEquals("", result.text)
    }
}
