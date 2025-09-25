package com.ai.inty.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable

/** Keep Talking按钮组件 */
@Composable
fun KeepTalkingButton(
    visible: Boolean,
    onClick: () -> Unit,
) {
  if (!visible) return

  Row(
      modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
      horizontalArrangement = androidx.compose.foundation.layout.Arrangement.Start,
  ) {
    Box(
        modifier =
            Modifier.width(80.dp)
                .height(32.dp)
                .background(Color.Transparent, RoundedCornerShape(16.dp))
                .noRippleClickable { onClick() },
        contentAlignment = Alignment.Center,
    ) {
      // 播放按钮图标 (>>)
      Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            text = stringResource(R.string.play_button_symbol),
            color = Color.White,
            fontSize = 12.sp,
        )
        Spacer(modifier = Modifier.width(0.dp))
        Text(
            text = stringResource(R.string.play_button_symbol),
            color = Color.White,
            fontSize = 12.sp,
        )
      }
    }
  }
}
