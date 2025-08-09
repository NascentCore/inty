package com.ai.inty.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.TextUnit
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class ChatTextFormatterTest {
    @Test
    fun formatChatMessage_appliesItalicStyleWithinBrackets() {
        val input = "Hello (world)"
        val result = ChatTextFormatter.formatChatMessage(
            text = input,
            fontSize = TextUnit.Unspecified,
            fontWeight = FontWeight.Normal,
            normalColor = Color.Black,
            italicColor = Color.Red,
        )

        // Text remains unchanged
        assertEquals(input, result.text)

        // Find span for the bracket content
        val italicSpan = result.spanStyles.find { span ->
            result.text.substring(span.start, span.end) == "world"
        }

        assertNotNull("Italic span for bracket content not found", italicSpan)
        assertEquals(FontStyle.Italic, italicSpan!!.item.fontStyle)
        assertEquals(Color.Red, italicSpan.item.color)
    }
}
