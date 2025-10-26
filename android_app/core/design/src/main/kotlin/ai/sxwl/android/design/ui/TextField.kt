package ai.sxwl.android.design.ui

import androidx.annotation.IntRange
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** 聊天输入框 */
@Composable
fun HeartMultiLineEditor(
    modifier: Modifier = Modifier,
    inputValue: String,
    onInputChange: (String) -> Unit,
    enableInput: Boolean = true,
    readOnly: Boolean = false,
    supportStr: String = "",
    textStyle: TextStyle =
        TextStyle(
            fontSize = 14.sp,
            fontWeight = FontWeight(400),
            color = Color(0x59FFFFFF),
            textAlign = TextAlign.Start,
            lineHeightStyle =
                LineHeightStyle(
                    alignment = LineHeightStyle.Alignment.Center,
                    trim = LineHeightStyle.Trim.Both
                )
        ),
    @IntRange(from = 0L) maxLength: Int = Int.MAX_VALUE,
    maxLines: Int = Int.MAX_VALUE,
    hintStr: String = "",
) {
    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        OutlinedTextField(
            value = inputValue,
            onValueChange = { str ->
                if (str.length in 0..maxLength) {
                    onInputChange(str)
                }
            },
            modifier = modifier,
            enabled = enableInput,
            readOnly = readOnly,
            textStyle = textStyle,
            maxLines = maxLines,
            placeholder = {
                if (hintStr.isNotEmpty()) {
                    Text(
                        text = hintStr,
                        fontSize = textStyle.fontSize,
                        fontWeight = textStyle.fontWeight,
                        color = textStyle.color,
                    )
                }
            },
            supportingText = {
                if (supportStr.isNotEmpty()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        Text(
                            text = supportStr,
                            fontSize = 12.sp,
                            lineHeight = 22.sp,
                            fontWeight = FontWeight.Normal,
                            color = Color(0x8CFFFFFF),
                            modifier = Modifier
                        )
                    }
                }
            },
            colors =
                OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.Transparent,
                    unfocusedBorderColor = Color.Transparent,
                    disabledBorderColor = Color.Transparent
                )
        )
    }
}

@Preview
@Composable
private fun PreviewChatInputUI() {
    var inputStr by remember { mutableStateOf("Input...") }
    HeartMultiLineEditor(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Color(0x1AFFFFFF)),
        inputValue = inputStr,
        onInputChange = { inputStr = it },
        maxLength = 20,
        maxLines = 3,
        supportStr = "${inputStr.length}/20",
    )
}
