package com.ai.intellimate.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * 单行文本输入框组件
 *
 * @param label 标签文本
 * @param labelFontSize 标签字体大小
 * @param inputValue 输入值
 * @param onValueChange 值变化回调
 * @param inputFontSize 输入框字体大小
 * @param placeholder 占位符文本
 * @param capitalizeFirstLetter 是否将首字母大写，默认为 true
 */
@Composable
fun SingleLineTextInputField(
    label: String,
    labelFontSize: TextUnit,
    inputValue: String,
    onValueChange: (String) -> Unit,
    inputFontSize: TextUnit,
    placeholder: String,
    capitalizeFirstLetter: Boolean = true,
) {
    Column {
        Text(
            text = label,
            fontSize = labelFontSize,
            color = Color.White,
            fontWeight = FontWeight.Medium,
        )
        Spacer(modifier = Modifier.height(12.dp))

        val cornerRadiusRatio = 0.7f
        val cornerRadius = cornerRadiusRatio * inputFontSize.value
        OutlinedTextField(
            value = inputValue,
            onValueChange = onValueChange,
            keyboardOptions =
                KeyboardOptions(
                    imeAction = ImeAction.Done,
                    capitalization =
                        if (capitalizeFirstLetter) KeyboardCapitalization.Sentences
                        else KeyboardCapitalization.None,
                ),
            placeholder = {
                Text(text = placeholder, fontSize = inputFontSize, color = Color.White.copy(0.5f))
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            textStyle = TextStyle(color = Color.White, fontSize = inputFontSize),
            colors =
                OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.White.copy(0.2f),
                    unfocusedBorderColor = Color.White.copy(0.2f),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    focusedPlaceholderColor = Color.White.copy(0.5f),
                    unfocusedPlaceholderColor = Color.White.copy(0.5f),
                    focusedContainerColor = Color(0x1A78599A),
                    unfocusedContainerColor = Color(0x1A78599A),
                    cursorColor = Color.White,
                ),
            shape = RoundedCornerShape(cornerRadius.dp),
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun SingleLineTextInputFieldPreview() {
    var text by remember { mutableStateOf("") }

    SingleLineTextInputField(
        label = "Name *",
        labelFontSize = 16.sp,
        inputValue = text,
        onValueChange = { text = it },
        inputFontSize = 16.sp,
        placeholder = "Name your IntelliMate",
        capitalizeFirstLetter = true,
    )
}

@Preview(showBackground = true)
@Composable
private fun SingleLineTextInputFieldWithTextPreview() {
    var text by remember { mutableStateOf("My IntelliMate") }

    SingleLineTextInputField(
        label = "Character Name *",
        labelFontSize = 18.sp,
        inputValue = text,
        onValueChange = { text = it },
        inputFontSize = 18.sp,
        placeholder = "Enter character name",
        capitalizeFirstLetter = true,
    )
}

@Preview(showBackground = true)
@Composable
private fun SingleLineTextInputFieldNoCapitalizePreview() {
    var text by remember { mutableStateOf("") }

    SingleLineTextInputField(
        label = "Description",
        labelFontSize = 16.sp,
        inputValue = text,
        onValueChange = { text = it },
        inputFontSize = 16.sp,
        placeholder = "Enter description (no auto-capitalize)",
        capitalizeFirstLetter = false,
    )
}
