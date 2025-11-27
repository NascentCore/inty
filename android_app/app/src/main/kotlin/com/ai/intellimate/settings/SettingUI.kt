package com.ai.intellimate.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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

/** 退出登录按钮组件 */

@Composable
fun LogoutButton(modifier: Modifier = Modifier, onLogout: () -> Unit = {}) {
    Column(
        modifier = modifier
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
            .clickable { onLogout() }
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

@Preview
@Composable
private fun 预览登出按钮() {
    LogoutButton()
}
