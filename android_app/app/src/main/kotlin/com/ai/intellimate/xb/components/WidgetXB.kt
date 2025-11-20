package com.ai.intellimate.xb.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.TextUnitType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun MultiLineBasicTextField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String = "",
    minLines: Int = 1,
    maxLines: Int = Int.MAX_VALUE,
    maxLength: Int = 800,
    showMaxLength: Boolean = true,
    showBorder: Boolean = true,
    fontSize: TextUnit = 16.sp,
    counterColor: Color = Color.Gray,  // 右下角字数颜色
    backgroundColor: Color = Color(0x1A78599A),
    cursorColor: Color = Color.White,
    keyboardOptions: KeyboardOptions = KeyboardOptions(
        imeAction = ImeAction.Default,
        capitalization = KeyboardCapitalization.Sentences, // 每句话首字母自动大写
    ),
    keyboardActions: KeyboardActions = KeyboardActions.Default,
) {
    val interactionSource = remember { MutableInteractionSource() }

    // ⭐ 自动限制最大字符数
    val safeValue = remember(value) { value.take(maxLength) }
    LaunchedEffect(value) {
        if (value.length > maxLength) {
            onValueChange(value.take(maxLength))
        }
    }
    val lineHeight = fontSize.plusSp(4)
    
    // 根据实际的 lineHeight 和 padding 计算高度
    // 将 lineHeight 从 sp 转换为 dp：在默认字体缩放下，1 sp ≈ 1 dp
    // 直接使用数值作为 dp 以匹配渲染的行高
    val calculatedHeight = remember(minLines, lineHeight, showMaxLength) {
        if (minLines > 1) {
            // 使用 lineHeight.value 作为 dp（在默认字体缩放下大致正确）
            // 这确保高度随实际的 fontSize/lineHeight 缩放
            val lineHeightInDp = lineHeight.value
            val topPadding = 16
            val bottomPadding = if (showMaxLength) 24 else 16
            (minLines * lineHeightInDp + topPadding + bottomPadding).dp
        } else {
            null
        }
    }

    Box {
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            cursorBrush = SolidColor(cursorColor),
            minLines = minLines,
            maxLines = maxLines,
            keyboardOptions = keyboardOptions,
            keyboardActions = keyboardActions,
            modifier =
                Modifier.fillMaxWidth()
                    .background(color = backgroundColor, shape = RoundedCornerShape(12.dp))
                    .conditional(showBorder) {
                        border(
                            width = 1.dp,
                            color = Color.White.copy(0.2f),
                            shape = RoundedCornerShape(12.dp),
                        )
                    }
                    .padding(top = 16.dp, start = 16.dp, end = 16.dp, bottom = if (showMaxLength) 24.dp else 16.dp)
                    .let { if (calculatedHeight != null) it.height(calculatedHeight) else it },
            textStyle = TextStyle(color = Color.White, fontSize = fontSize, lineHeight = lineHeight),
            interactionSource = interactionSource,

            decorationBox = { innerTextField ->
                Box {
                    if (value.isEmpty()) {
                        Text(text = placeholder, fontSize = fontSize, lineHeight = lineHeight, color = Color.White.copy(0.5f))
                    }
                    innerTextField()
                }
            }
        )

        // ⭐ 右下角字符计数
        if (showMaxLength) {
            Text(
                text = "${safeValue.length} / $maxLength",
                style = TextStyle(
                    fontSize = fontSize.plusSp(-4),
                    color = counterColor
                ),
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(bottom = 8.dp, end = 12.dp)
            )
        }

    }
}


inline fun Modifier.conditional(
    condition: Boolean,
    modifier: Modifier.() -> Modifier
): Modifier {
    return if (condition) {
        this.modifier()
    } else {
        this
    }
}

fun TextUnit.plusSp(delta: Int): TextUnit =
    TextUnit(this.value + delta, TextUnitType.Sp)
