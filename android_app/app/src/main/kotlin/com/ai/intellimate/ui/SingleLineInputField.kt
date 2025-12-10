package com.ai.intellimate.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R

val NameInputKeyBoardOption = KeyboardOptions(capitalization = KeyboardCapitalization.Words)

/** 单行文本输入框框 */
@Composable
fun SingleLineInputField(
    value: String,
    onValueChange: (String) -> Unit,
    keyboardOptions: KeyboardOptions,
    title: String? = null,
    placeholder: String? = null,
) {
    Column {
        title?.let {
            Text(text = it, fontSize = 16.sp, color = Color.White, fontWeight = FontWeight.Medium)
            Spacer(modifier = Modifier.height(12.dp))
        }
        // 禁用字体缩放，避免视觉抖动
        CompositionLocalProvider(
            LocalDensity provides
                Density(
                    density = LocalDensity.current.density,
                    fontScale = 1f, // 核心：禁用字体缩放
                )
        ) {
            Row(
                modifier =
                    Modifier.padding(
                            horizontal = if (title != null) 0.dp else 16.dp,
                            vertical = 0.dp,
                        )
                        .fillMaxWidth()
                        .heightIn(min = 48.dp)
                        .background(Color.White.copy(0.1f), RoundedCornerShape(8.dp))
                        .border(
                            width = 0.5.dp,
                            color = Color.White.copy(0.2f),
                            shape = RoundedCornerShape(8.dp),
                        ),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IntySmallTextField(
                    modifier = Modifier.weight(1f),
                    value = value,
                    selection = value.length,
                    onValueChange = onValueChange,
                    maxLength = 50,
                    placeholder = {
                        Text(
                            text = placeholder ?: stringResource(R.string.str_name_placeholder),
                            color = Color.White.copy(0.55f),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Normal,
                        )
                    },
                    keyboardOptions = keyboardOptions,
                )
            }
        }
    }
}
