package ai.sxwl.android.common.base

import ai.sxwl.android.design.theme.IntelliMateTheme
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable

/**
 * 简单封装的activity的基类，继承自ComponentActivity而非AppcompatActivity
 */
abstract class BaseActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(statusBarStyle = SystemBarStyle.dark(scrim = Color.TRANSPARENT))
        //非UI数据初始化
        initConfigData()
        //initUI
        setContent {
            //IntelliMate的app风格是dark模式
            IntelliMateTheme(darkTheme = true, dynamicColor = false) {
                ConfigComposeUI()
            }
        }
    }

    open fun initConfigData() {}

    @Composable
    open fun ConfigComposeUI() {
    }

}
