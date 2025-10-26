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
 * 简单封装activity的基础类，继承自ComponentActivity而不是AppcompatActivity
 */
abstract class BaseActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(statusBarStyle = SystemBarStyle.dark(scrim = Color.TRANSPARENT))
//非UI数据初始化
        initConfigData()
//初始化用户界面
        setContent {
//IntelliMate的应用风格是黑暗模式
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
