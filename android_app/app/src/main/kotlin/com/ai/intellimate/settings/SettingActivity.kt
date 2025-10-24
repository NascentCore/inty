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
import com.ai.intellimate.R
import com.ai.inty.MainActivity
import com.ai.inty.viewmodels.MainViewModel

/** 设置页面 */
class SettingActivity : BaseActivity() {

    companion object {

        /**
         * 启动设置界面
         * @param context 上下文context
         */
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
                // 使用MainViewModel的logout方法，不重启应用
                mainViewModel.logout()
                // 显示退出成功提示
                val str =
                    if (isDelete) getString(R.string.delete_account_successfully)
                    else getString(R.string.logout_successfully)
                ToastUtils.showShort(str)
                // 返回到主页面
                val intent = Intent(this@SettingActivity, MainActivity::class.java)
                intent.flags =
                    Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                startActivity(intent)
                finish()
            },
        )
    }
}
