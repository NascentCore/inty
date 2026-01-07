package com.ai.intellimate.ui.components

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/**
 * 举报按钮组件
 *
 * 用于在全屏图片查看器中显示举报按钮，样式与 Crop 按钮一致。 包含图标和"Report"文字，点击后触发举报回调。
 *
 * @param onClick 点击按钮时的回调
 * @param modifier 修饰符
 * @param iconSize 图标大小，默认为 16.dp
 * @param textFontSize 文字字体大小，默认为 12.sp
 */
@Composable
fun ReportButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    iconSize: Dp = 16.dp,
    textFontSize: TextUnit = 12.sp,
) {
    Box(
        modifier =
            modifier
                .padding(8.dp)
                .background(
                    color = Color.Black.copy(alpha = 0.5f),
                    shape = RoundedCornerShape(iconSize),
                )
                .noRippleClickable { onClick() }
                .padding(UiConfigs.CreateRole.VisualAppearance.FaceEditPillPadding)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Icon(
                imageVector = Icons.Filled.Flag,
                contentDescription = stringResource(R.string.report_button_content_description),
                modifier = Modifier.size(iconSize),
                tint = Color.White,
            )
            Text(
                text = stringResource(R.string.str_report),
                color = Color.White,
                fontSize = textFontSize,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}
