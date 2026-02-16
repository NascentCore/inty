package ai.sxwl.android.common.utils

import ai.sxwl.android.utils.AppUtils
import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext

/** 简单封装的一些工具函数 */
object HeartAppUtils {

    /** 判断app是否debug的包 */
    @Composable
    fun isAppDebugMode(): Boolean {
        val context = LocalContext.current
        val isDebugMode by
            AppUtils.debugModeFlow(context).collectAsState(initial = AppUtils.isDebugMode(context))
        return isDebugMode
    }

    /** 判断app是否debug的包 */
    fun isAppDebugMode(context: Context): Boolean {
        return AppUtils.isDebugMode(context)
    }
}
