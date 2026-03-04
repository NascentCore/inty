package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.model.GENDER
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R

/** 性别选择项组件 */
@Composable
internal fun GenderItem(gender: GENDER, selected: Boolean, onClick: () -> Unit) {
    val genderIcon =
        when (gender) {
            GENDER.MALE -> if (selected) R.drawable.gender_male_selected else R.drawable.gender_male
            GENDER.FEMALE ->
                if (selected) R.drawable.gender_female_selected else R.drawable.gender_female
            GENDER.OTHER ->
                if (selected) R.drawable.gender_other_selected else R.drawable.gender_other
        }

    val genderText =
        when (gender) {
            GENDER.MALE -> "He/Him"
            GENDER.FEMALE -> "She/Her"
            GENDER.OTHER -> "They/Them"
        }

    Column(
        modifier = Modifier.noRippleClickable { onClick() },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier =
                Modifier.size(80.dp)
                    .background(color = Color.White.copy(0.1f), shape = CircleShape)
                    .then(
                        if (selected) {
                            Modifier.border(
                                brush =
                                    Brush.linearGradient(
                                        colors = listOf(Color(0xffC122FF), Color(0xffFF905D))
                                    ),
                                width = 2.dp,
                                shape = CircleShape,
                            )
                        } else {
                            Modifier.border(
                                width = 0.5.dp,
                                color = Color.White.copy(0.2f),
                                shape = CircleShape,
                            )
                        }
                    ),
            contentAlignment = Alignment.Center,
        ) {
            Image(
                modifier = Modifier.size(38.dp),
                painter = painterResource(genderIcon),
                contentDescription = null,
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(
            text = genderText,
            color = if (selected) Color.White else Color.White.copy(0.55f),
            fontSize = 14.sp,
        )
    }
}

/** 年龄选择项组件 */
@Composable
internal fun AgeItem(
    modifier: Modifier,
    text: String,
    isSelected: Boolean = false,
    onSelected: () -> Unit = {},
) {
    Box(
        modifier =
            modifier
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(24.dp))
                .then(
                    if (isSelected) {
                        Modifier.border(
                            brush =
                                Brush.linearGradient(
                                    colors = listOf(Color(0xffC122FF), Color(0xffFF905D))
                                ),
                            width = 2.dp,
                            shape = RoundedCornerShape(24.dp),
                        )
                    } else {
                        Modifier.border(
                            width = 0.5.dp,
                            color = Color.White.copy(0.2f),
                            shape = RoundedCornerShape(24.dp),
                        )
                    }
                )
                .noRippleClickable { onSelected() },
        contentAlignment = Alignment.Center,
    ) {
        if (isSelected) {
            Text(
                text = text,
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
            )
        } else {
            Text(
                text = text,
                color = Color.White.copy(0.55f),
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
            )
        }
    }
}

/**
 * MBTI 性格类型选择 Chip（Myers-Briggs Type Indicator）。
 *
 * 使用场景：
 * - 注册信息弹层中展示 16 种 MBTI 类型（如 INTJ、ENFP）的可选项。
 * - 在紧凑网格布局里保持清晰的选中态与未选中态，降低用户认知负担。
 *
 * 预期视觉：
 * - 未选中：半透明深色底 + 细边框，保持整体层次不抢焦点。
 * - 选中：渐变边框 + 高亮文字，便于在 16 项中快速识别当前选择。
 *
 * 可配置项：
 * @param modifier 外部布局修饰器（用于网格宽度/高度、行列间距控制）。
 * @param mbtiType 展示的 MBTI 代码（例如 INTP）。
 * @param selected 当前项是否被选中。
 * @param onClick 点击该项时的回调。
 */
@Composable
internal fun MbtiTypeChip(
    modifier: Modifier = Modifier,
    mbtiType: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val cornerRadius = dimensionResource(R.dimen.reg_info_mbti_chip_corner_radius)
    val borderWidth = dimensionResource(R.dimen.reg_info_mbti_chip_border_width)
    val chipPaddingHorizontal = dimensionResource(R.dimen.reg_info_mbti_chip_padding_horizontal)
    val chipPaddingVertical = dimensionResource(R.dimen.reg_info_mbti_chip_padding_vertical)

    Box(
        modifier =
            modifier
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(cornerRadius))
                .then(
                    if (selected) {
                        Modifier.border(
                            brush =
                                Brush.linearGradient(
                                    colors = listOf(Color(0xffC122FF), Color(0xffFF905D))
                                ),
                            width = borderWidth,
                            shape = RoundedCornerShape(cornerRadius),
                        )
                    } else {
                        Modifier.border(
                            width = borderWidth,
                            color = Color.White.copy(0.2f),
                            shape = RoundedCornerShape(cornerRadius),
                        )
                    }
                )
                .noRippleClickable { onClick() }
                .padding(horizontal = chipPaddingHorizontal, vertical = chipPaddingVertical),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = mbtiType,
            color = if (selected) Color.White else Color.White.copy(0.7f),
            style = MaterialTheme.typography.labelLarge,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
        )
    }
}

/** 关闭按钮组件 */
@Composable
internal fun CloseButton(onClose: () -> Unit) {
    Image(
        modifier =
            Modifier.padding(end = 16.dp, top = 16.dp).size(18.dp, 18.dp).noRippleClickable {
                onClose()
            },
        painter = painterResource(R.drawable.close),
        contentDescription = null,
    )
}

/** 标题文本组件 */
@Composable
internal fun TitleText(title: String, modifier: Modifier = Modifier) {
    Text(
        modifier = modifier.padding(horizontal = 24.dp),
        text = title,
        fontSize = 26.sp,
        fontWeight = FontWeight.Bold,
        color = Color.White,
    )
}

/** 副标题文本组件 */
@Composable
internal fun SubtitleText(subtitle: String, modifier: Modifier = Modifier) {
    Text(
        modifier = modifier.padding(horizontal = 24.dp),
        text = subtitle,
        fontSize = 14.sp,
        fontWeight = FontWeight.Normal,
        color = Color.White.copy(0.55f),
    )
}

/** 标签文本组件 */
@Composable
internal fun LabelText(label: String, modifier: Modifier = Modifier) {
    Text(
        modifier = modifier.padding(horizontal = 24.dp),
        text = label,
        fontSize = 14.sp,
        fontWeight = FontWeight.SemiBold,
        color = Color.White,
    )
}

// Preview 函数
@Preview(showBackground = true)
@Composable
private fun GenderItemPreview() {
    GenderItem(gender = GENDER.MALE, selected = true, onClick = {})
}

@Preview(showBackground = true)
@Composable
private fun AgeItemPreview() {
    AgeItem(
        modifier = Modifier.fillMaxWidth().height(48.dp),
        text = "18-20",
        isSelected = true,
        onSelected = {},
    )
}
