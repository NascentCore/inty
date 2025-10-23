package com.ai.inty.ui.components

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R

/** 通用渐变按钮组件 */
@Composable
fun GradientButton(text: String, onSave: () -> Unit, modifier: Modifier = Modifier) {
    Box(
        modifier =
            modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .height(50.dp)
                .background(
                    brush =
                        Brush.linearGradient(colors = listOf(Color(0xFFC122FF), Color(0xFFFF905D))),
                    shape = RoundedCornerShape(25.dp),
                )
                .noRippleClickable { onSave() }
    ) {
        Text(
            modifier = Modifier.align(Alignment.Center),
            text = text,
            fontSize = 16.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
        )
    }
}

/** 提交按钮组件 */
@Composable
fun SubmitButton(onSubmit: () -> Unit) {
    GradientButton(text = stringResource(R.string.submit_button), onSave = onSubmit)
}

/** 进入按钮组件 */
@Composable
fun EnterButton(onEnter: () -> Unit) {
    GradientButton(text = stringResource(R.string.enter), onSave = onEnter)
}

// Preview 函数
@Preview(showBackground = true)
@Composable
private fun GradientButtonPreview() {
    GradientButton(text = "提交", onSave = {})
}

@Preview(showBackground = true)
@Composable
private fun SubmitButtonPreview() {
    SubmitButton(onSubmit = {})
}

@Preview(showBackground = true)
@Composable
private fun EnterButtonPreview() {
    EnterButton(onEnter = {})
}
