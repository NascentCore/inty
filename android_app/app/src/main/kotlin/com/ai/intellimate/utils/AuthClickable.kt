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

/**
 * 带认证检查的可点击组件
 * 如果用户未登录，会跳转到登录页面
 *
 * @deprecated 已废弃：应用已移除 guest 账户流程，isGuestUser() 检查已不再需要。
 * 现在只需要检查是否登录即可：IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
 */
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
                // 检查是否已登录（已移除 guest 用户检查，因为不再支持 guest 账户）
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    onClick()
                } else {
                    // 未登录时跳转到登录页面
                    context.startActivity(Intent(context, LoginActivity::class.java))
                }
            }
        }

    // 将 modifier 传递给内容
    content(authModifier)
}
