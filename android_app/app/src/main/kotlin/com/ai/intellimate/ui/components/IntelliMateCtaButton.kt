package com.ai.intellimate.ui.components

import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.design.theme.AppColors
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.ai.intellimate.ui.UiConfigs

/**
 * 与「Create My IntelliMate」一致的 CTA 按钮组件，粉→橙水平渐变、全宽圆角、白字。
 *
 * 适用范围：创建/编辑 IntelliMate 页底部、Explore 列表底部「Explore More」等需要强 CTA 的场景。
 *
 * 预期视觉效果：全宽、圆角 25.dp、高 56.dp，水平渐变（粉红→橙），白字 18.sp SemiBold；
 * loading 时显示白色 CircularProgressIndicator，禁用点击。
 *
 * 可配置项：[text] 按钮文案、[onClick] 点击回调、[modifier]、[isLoading]、[enabled]。
 */
@Composable
fun IntelliMateCtaButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    isLoading: Boolean = false,
    enabled: Boolean = true,
) {
    var lastClickTime by remember { mutableLongStateOf(0L) }

    Button(
        onClick = {
            val currentTime = System.currentTimeMillis()
            if (AntiClick.isValidClick(lastClickTime)) {
                lastClickTime = currentTime
                onClick()
            }
        },
        enabled = enabled && !isLoading,
        colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(UiConfigs.Shape.PrimaryButton),
        modifier =
            modifier
                .fillMaxWidth()
                .height(UiConfigs.Size.CtaButtonHeight)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors =
                                listOf(
                                    AppColors.IntelliMateCtaGradientStart,
                                    AppColors.IntelliMateCtaGradientEnd,
                                ),
                        ),
                    shape = RoundedCornerShape(UiConfigs.Shape.PrimaryButton),
                ),
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                color = Color.White,
                modifier = Modifier.size(24.dp),
                strokeWidth = 2.5.dp,
            )
        } else {
            Text(
                text = text,
                fontSize = UiConfigs.Typography.ButtonLarge,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
        }
    }
}
