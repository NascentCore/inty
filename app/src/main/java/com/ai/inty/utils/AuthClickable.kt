package com.ai.inty.utils

import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.ai.inty.LoginActivity
import com.inty.utils.storage.IntySetting

@Composable
fun AuthClickable(
  modifier: Modifier = Modifier,
  onClick: () -> Unit,
  content: @Composable (Modifier) -> Unit
) {
  val context = LocalContext.current
  
  // 创建带有认证检查的 modifier
  val authModifier = modifier.clickable {
    // 检查是否正式登录（非游客且已登录）
    if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
      onClick()
    } else {
      // 未登录或游客时跳转到登录页面
      context.startActivity(Intent(context, LoginActivity::class.java))
    }
  }
  
  // 将 modifier 传递给内容
  content(authModifier)
}