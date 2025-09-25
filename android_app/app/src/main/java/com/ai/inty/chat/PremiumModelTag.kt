package com.ai.inty.chat

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable

/** Premium Model标签组件 */
@Composable
fun PremiumModelTag(
    isPremiumModel: Boolean,
    onClick: () -> Unit,
) {
  Row(
      modifier =
          Modifier.padding(horizontal = 16.dp)
              .height(28.dp)
              .background(
                  brush =
                      if (isPremiumModel) {
                        // 激活状态：渐变背景
                        Brush.horizontalGradient(
                            colors =
                                listOf(
                                    Color(0xFF00EEFF),
                                    Color(0xFF0B50FF),
                                    Color(0xFFFF00D0),
                                )
                        )
                      } else {
                        // 置灰状态：半透明灰色
                        Brush.horizontalGradient(
                            colors =
                                listOf(
                                    Color(0xFF595959),
                                    Color(0xFF9E9E9E),
                                    Color(0xFF686868),
                                )
                        )
                      },
                  shape = RoundedCornerShape(16.dp),
              )
              .noRippleClickable { onClick() }
              .padding(horizontal = 10.dp),
      verticalAlignment = Alignment.CenterVertically,
      horizontalArrangement = Arrangement.Center,
  ) {
    // V图标
    Image(
        painter =
            painterResource(
                if (isPremiumModel) R.drawable.icon_vip_flag_on else R.drawable.icon_vip_flag_off
            ),
        contentDescription = "",
        modifier = Modifier.size(20.dp),
    )

    // Premium model文本
    Text(
        text = stringResource(R.string.settings_premium_model),
        color = Color.White,
        fontSize = 10.sp,
        lineHeight = 10.sp,
        fontWeight = FontWeight.Normal,
    )
  }
}
