package com.ai.inty.utils

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.sp
import androidx.compose.ui.Modifier
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import android.content.Intent
import android.content.Context
import com.ai.inty.base.noRippleClickable
import androidx.core.net.toUri


/**
 * 文本样式工具类
 * 提供常用的文本格式化功能
 */
object TextStyleUtils {

    /**
     * 创建带下划线的可点击文本
     *
     * @param text 文本内容
     * @param color 文本颜色
     * @param fontSize 字体大小
     * @return 格式化后的AnnotatedString
     */
    fun createLinkText(
        text: String,
        fontSize: TextUnit = 12.sp,
    ): AnnotatedString = buildAnnotatedString {
        withStyle(
            SpanStyle(
                color = Color.White,
                fontSize = fontSize,
                textDecoration = TextDecoration.Underline
            )
        ) {
            append(text)
        }
    }

    /**
     * Helper function to create clickable text that opens a URL
     */
    @Composable
    fun BuildLink(
        context: Context,
        text: String,
        url: String,
        fontSize: TextUnit = 12.sp
    ) = Text(
        text = buildAnnotatedString {
            withStyle(
                SpanStyle(
                    color = Color.White,
                    fontSize = fontSize,
                    textDecoration = TextDecoration.Underline
                )
            ) {
                append(text)
            }
        },
        modifier = Modifier.noRippleClickable(onClick = {
            val intent = Intent(
                Intent.ACTION_VIEW,
                url.toUri()
            )
            context.startActivity(intent)
        })
    )

    /**
     * 创建带样式的文本
     *
     * @param text 文本内容
     * @param color 文本颜色
     * @param fontSize 字体大小
     * @param fontWeight 字体粗细
     * @param fontStyle 字体样式
     * @return 格式化后的AnnotatedString
     */
    fun createStyledText(
        text: String,
        color: Color,
        fontSize: TextUnit,
        fontWeight: FontWeight = FontWeight.Normal,
        fontStyle: FontStyle? = null,
    ): AnnotatedString = buildAnnotatedString {
        withStyle(
            SpanStyle(
                color = color,
                fontSize = fontSize,
                fontWeight = fontWeight,
                fontStyle = fontStyle
            )
        ) {
            append(text)
        }
    }

    /**
     * 创建混合样式文本
     *
     * @param parts 文本片段列表，每个片段包含文本和样式
     * @return 格式化后的AnnotatedString
     */
    fun createMixedText(parts: List<TextPart>): AnnotatedString = buildAnnotatedString {
        parts.forEach { part ->
            withStyle(
                SpanStyle(
                    color = part.color,
                    fontSize = part.fontSize,
                    fontWeight = part.fontWeight,
                    fontStyle = part.fontStyle,
                    textDecoration = part.textDecoration
                )
            ) {
                append(part.text)
            }
        }
    }
}

/**
 * 文本片段数据类
 */
data class TextPart(
    val text: String,
    val color: Color,
    val fontSize: TextUnit,
    val fontWeight: FontWeight = FontWeight.Normal,
    val fontStyle: FontStyle? = null,
    val textDecoration: TextDecoration? = null,
) 