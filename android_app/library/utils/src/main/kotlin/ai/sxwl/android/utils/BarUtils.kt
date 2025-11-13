package ai.sxwl.android.utils

import android.app.Activity
import android.content.res.Resources
import android.graphics.Color
import android.os.Build
import android.view.Window
import android.view.WindowManager
import androidx.annotation.ColorInt
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat

/** 状态栏和导航栏工具类 提供状态栏和导航栏相关的工具方法 */
object BarUtils {

    // ==================== 状态栏相关 ====================

    /** 获取状态栏高度 */
    fun getStatusBarHeight(): Int {
        val resources = Resources.getSystem()
        val resourceId = resources.getIdentifier("status_bar_height", "dimen", "android")
        return if (resourceId > 0) {
            resources.getDimensionPixelSize(resourceId)
        } else {
            0
        }
    }

    /** 设置状态栏可见性 */
    fun setStatusBarVisibility(activity: Activity, isVisible: Boolean) {
        try {
            val window = activity.window ?: return
            setStatusBarVisibility(window, isVisible)
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 设置状态栏可见性 */
    fun setStatusBarVisibility(window: Window, isVisible: Boolean) {
        try {
            if (isVisible) {
                window.clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN)
            } else {
                window.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN)
            }
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 判断状态栏是否可见 */
    fun isStatusBarVisible(activity: Activity): Boolean {
        return try {
            val window = activity.window ?: return true
            isStatusBarVisible(window)
        } catch (e: Exception) {
            true // 默认返回可见
        }
    }

    /** 判断状态栏是否可见 */
    fun isStatusBarVisible(window: Window): Boolean {
        return try {
            val flags = window.attributes.flags
            (flags and WindowManager.LayoutParams.FLAG_FULLSCREEN) == 0
        } catch (e: Exception) {
            true // 默认返回可见
        }
    }

    /** 设置状态栏颜色 */
    fun setStatusBarColor(activity: Activity, @ColorInt color: Int) {
        setStatusBarColor(activity.window, color)
    }

    /** 设置状态栏颜色 */
    fun setStatusBarColor(window: Window, @ColorInt color: Int) {
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
        window.statusBarColor = color
    }

    /** 获取状态栏颜色 */
    fun getStatusBarColor(activity: Activity): Int = getStatusBarColor(activity.window)

    /** 获取状态栏颜色 */
    fun getStatusBarColor(window: Window): Int {
        return try {
            window.statusBarColor
        } catch (e: Exception) {
            Color.TRANSPARENT
        }
    }

    /** 设置状态栏透明度 */
    fun setStatusBarAlpha(activity: Activity, alpha: Float) {
        setStatusBarAlpha(activity.window, alpha)
    }

    /** 设置状态栏透明度 */
    fun setStatusBarAlpha(window: Window, alpha: Float) {
        val color = getStatusBarColor(window)
        val alphaColor =
            Color.argb(
                (alpha * 255).toInt(),
                Color.red(color),
                Color.green(color),
                Color.blue(color),
            )
        setStatusBarColor(window, alphaColor)
    }

    /** 设置状态栏浅色模式 */
    fun setStatusBarLightMode(activity: Activity, isLightMode: Boolean) {
        try {
            val window = activity.window ?: return
            setStatusBarLightMode(window, isLightMode)
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 设置状态栏浅色模式 */
    fun setStatusBarLightMode(window: Window, isLightMode: Boolean) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                // API 30+ 使用 WindowInsetsController
                val controller: WindowInsetsControllerCompat? =
                    WindowCompat.getInsetsController(window, window.decorView)
                controller?.isAppearanceLightStatusBars = isLightMode
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                // API 23-29 使用系统UI标志
                var flags = window.decorView.systemUiVisibility
                flags =
                    if (isLightMode) {
                        flags or android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
                    } else {
                        flags and android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR.inv()
                    }
                window.decorView.systemUiVisibility = flags
            }
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 判断状态栏是否为浅色模式 */
    fun isStatusBarLightMode(activity: Activity): Boolean {
        return try {
            val window = activity.window ?: return false
            isStatusBarLightMode(window)
        } catch (e: Exception) {
            false
        }
    }

    /** 判断状态栏是否为浅色模式 */
    fun isStatusBarLightMode(window: Window): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                // API 30+ 使用 WindowInsetsController
                val controller: WindowInsetsControllerCompat? =
                    WindowCompat.getInsetsController(window, window.decorView)
                controller?.isAppearanceLightStatusBars ?: false
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                // API 23-29 检查系统UI标志
                val flags = window.decorView.systemUiVisibility
                (flags and android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR) != 0
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }

    // ==================== 导航栏相关 ====================

    /** 获取导航栏高度 */
    fun getNavBarHeight(): Int {
        val resources = Resources.getSystem()
        val resourceId = resources.getIdentifier("navigation_bar_height", "dimen", "android")
        return if (resourceId > 0) {
            resources.getDimensionPixelSize(resourceId)
        } else {
            0
        }
    }

    /** 设置导航栏可见性 */
    fun setNavBarVisibility(activity: Activity, isVisible: Boolean) {
        try {
            val window = activity.window ?: return
            setNavBarVisibility(window, isVisible)
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 设置导航栏可见性 */
    fun setNavBarVisibility(window: Window, isVisible: Boolean) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                // API 30+ 使用 WindowInsetsController
                val controller: WindowInsetsControllerCompat? =
                    WindowCompat.getInsetsController(window, window.decorView)
                if (isVisible) {
                    controller?.show(WindowInsetsCompat.Type.navigationBars())
                } else {
                    controller?.hide(WindowInsetsCompat.Type.navigationBars())
                }
            } else {
                // API 30以下使用系统UI标志
                var flags = window.decorView.systemUiVisibility
                flags =
                    if (isVisible) {
                        flags and android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION.inv()
                    } else {
                        flags or android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    }
                window.decorView.systemUiVisibility = flags
            }
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 判断导航栏是否可见 */
    fun isNavBarVisible(activity: Activity): Boolean {
        return isNavBarVisible(activity.window)
    }

    /** 判断导航栏是否可见 */
    fun isNavBarVisible(window: Window): Boolean {
        val flags = window.attributes.flags
        return (flags and WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS) == 0
    }

    /** 设置导航栏颜色 */
    fun setNavBarColor(activity: Activity, @ColorInt color: Int) {
        setNavBarColor(activity.window, color)
    }

    /** 设置导航栏颜色 */
    fun setNavBarColor(window: Window, @ColorInt color: Int) {
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
        window.navigationBarColor = color
    }

    /** 获取导航栏颜色 */
    fun getNavBarColor(activity: Activity): Int = getNavBarColor(activity.window)

    /** 获取导航栏颜色 */
    fun getNavBarColor(window: Window): Int {
        return try {
            window.navigationBarColor
        } catch (e: Exception) {
            Color.TRANSPARENT
        }
    }

    /** 设置导航栏浅色模式 */
    fun setNavBarLightMode(activity: Activity, isLightMode: Boolean) {
        try {
            val window = activity.window ?: return
            setNavBarLightMode(window, isLightMode)
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 设置导航栏浅色模式 */
    fun setNavBarLightMode(window: Window, isLightMode: Boolean) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                // API 30+ 使用 WindowInsetsController
                val controller: WindowInsetsControllerCompat? =
                    WindowCompat.getInsetsController(window, window.decorView)
                controller?.isAppearanceLightNavigationBars = isLightMode
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                // API 26-29 使用系统UI标志
                var flags = window.decorView.systemUiVisibility
                flags =
                    if (isLightMode) {
                        flags or android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
                    } else {
                        flags and android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR.inv()
                    }
                window.decorView.systemUiVisibility = flags
            }
        } catch (e: Exception) {
            // 静默处理异常
        }
    }

    /** 判断导航栏是否为浅色模式 */
    fun isNavBarLightMode(activity: Activity): Boolean {
        return try {
            val window = activity.window ?: return false
            isNavBarLightMode(window)
        } catch (e: Exception) {
            false
        }
    }

    /** 判断导航栏是否为浅色模式 */
    fun isNavBarLightMode(window: Window): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                // API 30+ 使用 WindowInsetsController
                val controller: WindowInsetsControllerCompat? =
                    WindowCompat.getInsetsController(window, window.decorView)
                controller?.isAppearanceLightNavigationBars ?: false
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                // API 26-29 检查系统UI标志
                val flags = window.decorView.systemUiVisibility
                (flags and android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR) != 0
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }

    // ==================== 组合操作 ====================

    /** 系统栏配置 */
    data class SystemBarConfig(
        val statusBarColor: Int = Color.TRANSPARENT,
        val statusBarLightMode: Boolean = false,
        val statusBarVisible: Boolean = true,
        val navBarColor: Int = Color.TRANSPARENT,
        val navBarLightMode: Boolean = false,
        val navBarVisible: Boolean = true,
    )

    /** 设置系统栏配置 */
    fun setSystemBarConfig(activity: Activity, config: SystemBarConfig) {
        setSystemBarConfig(activity.window, config)
    }

    /** 设置系统栏配置 */
    fun setSystemBarConfig(window: Window, config: SystemBarConfig) {
        // 设置状态栏
        setStatusBarVisibility(window, config.statusBarVisible)
        setStatusBarColor(window, config.statusBarColor)
        setStatusBarLightMode(window, config.statusBarLightMode)

        // 设置导航栏
        setNavBarVisibility(window, config.navBarVisible)
        setNavBarColor(window, config.navBarColor)
        setNavBarLightMode(window, config.navBarLightMode)
    }

    /** 设置沉浸式状态栏 */
    fun setImmersiveStatusBar(activity: Activity) {
        setImmersiveStatusBar(activity.window)
    }

    /** 设置沉浸式状态栏 */
    fun setImmersiveStatusBar(window: Window) {
        setSystemBarConfig(
            window,
            SystemBarConfig(
                statusBarColor = Color.TRANSPARENT,
                statusBarLightMode = false,
                statusBarVisible = true,
            ),
        )
    }

    /** 设置沉浸式导航栏 */
    fun setImmersiveNavBar(activity: Activity) {
        setImmersiveNavBar(activity.window)
    }

    /** 设置沉浸式导航栏 */
    fun setImmersiveNavBar(window: Window) {
        setSystemBarConfig(
            window,
            SystemBarConfig(
                navBarColor = Color.TRANSPARENT,
                navBarLightMode = false,
                navBarVisible = true,
            ),
        )
    }

    /** 设置全屏模式 */
    fun setFullScreen(activity: Activity) {
        setFullScreen(activity.window)
    }

    /** 设置全屏模式 */
    fun setFullScreen(window: Window) {
        setSystemBarConfig(window, SystemBarConfig(statusBarVisible = false, navBarVisible = false))
    }

    /** 获取系统栏总高度 */
    fun getSystemBarHeight(): Int {
        return getStatusBarHeight() + getNavBarHeight()
    }
}
