package ai.sxwl.android.common.base

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.design.theme.IntelliMateTheme
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable

/** 简单封装的activity的基类，继承自ComponentActivity而非AppcompatActivity */
abstract class BaseActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(statusBarStyle = SystemBarStyle.dark(scrim = Color.TRANSPARENT))

        // 页面追踪 - 记录页面访问
        PageTrackingHelper.trackActivityLifecycle(this, getPageName())
        
        // 非UI数据初始化
        initConfigData()
        // initUI
        setContent {
            // IntelliMate的app风格是dark模式
            IntelliMateTheme(darkTheme = true, dynamicColor = false) { ConfigComposeUI() }
        }
    }

    /** 获取页面名称，子类可以重写以提供自定义页面名称 */
    protected open fun getPageName(): String {
        return this.javaClass.simpleName
    }

    open fun initConfigData() {}

    @Composable open fun ConfigComposeUI() {}
}
