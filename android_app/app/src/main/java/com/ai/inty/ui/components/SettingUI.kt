package com.ai.inty.ui.components

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.ui.HeartRedDot
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R

/** 设置项容器组件 */
@Composable
fun SettingSection(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(
        modifier =
            modifier
                .padding(horizontal = 16.dp)
                .fillMaxWidth()
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                    width = 1.dp,
                    shape = RoundedCornerShape(8.dp),
                )
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(8.dp))
    ) {
        Spacer(Modifier.height(8.dp))
        content()
        Spacer(Modifier.height(8.dp))
    }
}

/** 设置项开关组件 */
@Composable
fun SettingSwitchItem(
    title: String,
    isEnabled: Boolean,
    onToggle: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier =
            modifier
                .fillMaxWidth()
                .height(48.dp)
                .padding(horizontal = 12.dp)
                .noRippleClickable {
                    onToggle()
                },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text = title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        Spacer(Modifier.weight(1f))
        Image(
            painter =
                if (isEnabled) painterResource(R.drawable.opened)
                else painterResource(R.drawable.closed),
            contentDescription = null,
        )
    }
}

/** 设置项导航组件 */
@Composable
fun SettingNavigationItem(
    title: String,
    subtitle: String? = null,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    showRedDot: Boolean = false,
) {
    Row(
        modifier =
            modifier
                .fillMaxWidth()
                .height(48.dp)
                .padding(horizontal = 12.dp)
                .noRippleClickable {
                    onClick()
                },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val SPACER_WIDTH = 10.dp
        Text(text = title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        Spacer(Modifier.weight(1f))
        if (showRedDot) {
            HeartRedDot()
            Spacer(Modifier.width(SPACER_WIDTH))
        }
        if (subtitle != null) {
            Text(
                text = subtitle,
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
                color = Color.White.copy(0.55f),
            )
            Spacer(Modifier.width(SPACER_WIDTH))
        }
        Image(painter = painterResource(R.drawable.icon_next), contentDescription = null)
    }
}

/** 设置项信息组件（只显示，不可点击） */
@Composable
fun SettingInfoItem(
    title: String,
    value: String,
    modifier: Modifier = Modifier,
    hasRedDot: Boolean = false,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(48.dp)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text = title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        Spacer(Modifier.weight(1f))
        Text(
            text = value,
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White.copy(0.55f),
        )
        if (hasRedDot) HeartRedDot()
    }
}

/** 分隔线组件 */
@Composable
fun SettingDivider() {
    Spacer(Modifier.height(4.dp))
    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        )
                )
    )
    Spacer(Modifier.height(4.dp))
}

/** 退出登录按钮组件 */
@Composable
fun LogoutButton(onLogout: () -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier =
            modifier
                .padding(horizontal = 16.dp)
                .fillMaxWidth()
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                    width = 1.dp,
                    shape = RoundedCornerShape(8.dp),
                )
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(8.dp))
                .noRippleClickable { onLogout() }
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp)
                .padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Spacer(Modifier.weight(1f))
            Text(
                text = stringResource(R.string.logout),
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            Spacer(Modifier.weight(1f))
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun SettingSwitchItemPreview() {
    SettingSwitchItem(
        title = stringResource(R.string.keep_talking),
        isEnabled = true,
        onToggle = {},
    )
}

@Preview(showBackground = true)
@Composable
private fun SettingNavigationItemPreview() {
    SettingNavigationItem(
        title = stringResource(R.string.email_support),
        subtitle = stringResource(R.string.support_email),
        onClick = {},
    )
}

@Preview(showBackground = true)
@Composable
private fun SettingInfoItemPreview() {
    SettingInfoItem(title = stringResource(R.string.about), value = "1.0.0")
}
