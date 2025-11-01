package com.ai.intellimate.settings

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.ToastUtils
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.R

/**
 * 设置页面
 *
 * @deprecated 已废弃：设置界面已整合到 MainActivity 中，使用 MainViewModel.showSettings() 在同一 Activity 内切换，避免 Activity 切换导致的 UI 闪动。
 */
@Deprecated(
    message = "已废弃：设置界面已整合到 MainActivity 中，请使用 MainViewModel.showSettings()",
    replaceWith = ReplaceWith("mainViewModel.showSettings()"),
    level = DeprecationLevel.WARNING
)
class SettingActivity : BaseActivity() {

    companion object {

        /**
         * 启动设置界面
         *
         * @param context 上下文context
         * @deprecated 已废弃：请使用 MainViewModel.showSettings() 在同一 Activity 内切换设置界面
         */
        @Deprecated(
            "已废弃：请使用 MainViewModel.showSettings()",
            ReplaceWith("mainViewModel.showSettings()"),
            DeprecationLevel.WARNING
        )
        fun launch(context: Context) {
            context.startActivity(Intent(context, SettingActivity::class.java))
        }
    }

    private val mainViewModel by viewModels<MainViewModel>()

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        SettingContent(
            modifier = Modifier.Companion
                .fillMaxSize()
                .background(HeartColor.primaryColor),
            onBack = { finish() },
            onLogout = { isDelete ->
                // 使用MainViewModel的logout方法
                mainViewModel.logout()
                // 显示退出成功提示
                val str =
                    if (isDelete) getString(R.string.delete_account_successfully)
                    else getString(R.string.logout_successfully)
                ToastUtils.showShort(str)
                // logout后，MainActivity会在Compose UI中定期检查登录状态（每200ms）
                // 一旦检测到状态变化，UI会立即从HomeScreen切换到SplashLoginUI
                // 只需要关闭Settings界面即可
                finish()
            },
        )
    }
}
