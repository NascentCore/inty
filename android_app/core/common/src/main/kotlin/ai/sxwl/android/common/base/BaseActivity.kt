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
        // 如果有额外的追踪参数，使用 trackPageView 直接调用；否则使用 trackActivityLifecycle
        val additionalParams = getAdditionalPageTrackingParams()
        if (additionalParams.isNotEmpty()) {
            // 使用 trackPageView 直接调用，传递额外参数
            PageTrackingHelper.trackPageView(getPageName(), javaClass.simpleName, additionalParams)
            // 注册生命周期监听器（不包含 trackPageView 调用）
            PageTrackingHelper.trackActivityLifecycleWithoutPageView(this)
        } else {
            // 使用默认的 trackActivityLifecycle
            PageTrackingHelper.trackActivityLifecycle(this, getPageName())
        }

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

    /** 获取额外的页面追踪参数，子类可以重写以提供额外的追踪参数（如 page_source） */
    protected open fun getAdditionalPageTrackingParams(): Map<String, Any> {
        return emptyMap()
    }

    open fun initConfigData() {}

    @Composable open fun ConfigComposeUI() {}
}
