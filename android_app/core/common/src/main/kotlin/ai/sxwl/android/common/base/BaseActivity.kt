package ai.sxwl.android.common.base

import ai.sxwl.android.design.theme.IntelliMateTheme
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable

/**
 * 简单封装的activity的基类，继承自ComponentActivity而非AppcompatActivity
 */
abstract class BaseActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        //非UI数据初始化
        initConfigData()
        //initUI
        setContent {
            IntelliMateTheme {
                ConfigComposeUI()
            }
        }
    }

    open fun initConfigData() {}

    @Composable
    open fun ConfigComposeUI() {
    }

}
