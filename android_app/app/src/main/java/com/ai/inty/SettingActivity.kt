package com.ai.inty

import android.os.Bundle
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.screens.SettingContent
import com.ai.inty.ui.theme.DarkPurple
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.MainViewModel
import com.therouter.TheRouter
import com.therouter.router.Route

/**
 * 设置页面
 */
@Route(path = Constant.ROUTE_SETTING)
class SettingActivity : BaseActivity() {

    private val mainViewModel by viewModels<MainViewModel>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            IntyTheme {
                SettingContent(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(DarkPurple),
                    onBack = {
                        finish()
                    },
                    onLogout = { isDelete ->
                        // 使用MainViewModel的logout方法，不重启应用
                        mainViewModel.logout()
                        // 显示退出成功提示
                        val str = if (isDelete) getString(R.string.delete_account_successfully)
                        else getString(R.string.logout_successfully)
                        Toast.makeText(
                            this@SettingActivity,
                            str,
                            Toast.LENGTH_SHORT
                        ).show()
                        // 返回到主页面
                        TheRouter.build(Constant.ROUTE_MAIN).navigation(this@SettingActivity)
                        finish()
                    }
                )
            }
        }
    }
}
