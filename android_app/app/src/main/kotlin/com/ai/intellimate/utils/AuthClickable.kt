package com.ai.intellimate.utils

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.AntiClick
import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.ai.intellimate.login.LoginActivity

@Composable
fun AuthClickable(
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    content: @Composable (Modifier) -> Unit,
) {
    val context = LocalContext.current
    var lastClickTime by remember { mutableLongStateOf(0L) }

    // 创建带有认证检查和防连击的 modifier
    val authModifier =
        modifier.clickable {
            val currentTime = System.currentTimeMillis()
            if (AntiClick.isValidClick(lastClickTime)) {
                lastClickTime = currentTime
                // 检查是否正式登录（非游客且已登录）
                if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                    onClick()
                } else {
                    // 未登录或游客时跳转到登录页面
                    context.startActivity(Intent(context, LoginActivity::class.java))
                }
            }
        }

    // 将 modifier 传递给内容
    content(authModifier)
}
