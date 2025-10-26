package ai.sxwl.android.common.utils

import android.content.Context
import android.content.pm.ApplicationInfo
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

/** 简单封装的一些工具函数 */
object HeartAppUtils {
    /** 判断app是否debug的包 */
    @Composable
    fun isAppDebugMode(): Boolean {
        val context = LocalContext.current
        return (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
    }

    /** 判断app是否debug的包 */
    fun isAppDebugMode(context: Context): Boolean {
        return (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
    }
}
