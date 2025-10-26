package com.ai.intellimate.utils

import ai.sxwl.android.design.noRippleClickable
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

/** 文本样式工具类提供常用的文本编辑功能 */
object TextStyleUtils {

    /** 创建可打开 URL 的可点击文本的辅助函数 */
    @Composable
    fun BuildLink(context: Context, text: String, url: String, fontSize: TextUnit) =
        Text(
            text =
                buildAnnotatedString {
                    withStyle(
                        SpanStyle(
                            color = Color.White,
                            fontSize = fontSize,
                            textDecoration = TextDecoration.Underline,
                        )
                    ) {
                        append(text)
                    }
                },
            modifier =
                Modifier.noRippleClickable(
                    onClick = {
                        val intent = Intent(Intent.ACTION_VIEW, url.toUri())
                        context.startActivity(intent)
                    }
                ),
        )
}
