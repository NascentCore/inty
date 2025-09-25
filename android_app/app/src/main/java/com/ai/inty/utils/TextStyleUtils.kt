package com.ai.inty.utils

import android.content.Context
import android.content.Intent
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit
import androidx.core.net.toUri
import com.ai.inty.base.noRippleClickable


/**
 * 文本样式工具类
 * 提供常用的文本格式化功能
 */
object TextStyleUtils {

    /**
     * Helper function to create clickable text that opens a URL
     */
    @Composable
    fun BuildLink(
        context: Context,
        text: String,
        url: String,
        fontSize: TextUnit,
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

}
