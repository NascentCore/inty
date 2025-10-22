package ai.sxwl.android.utils

import android.app.Application
import android.content.Context
import androidx.startup.Initializer

/**
 * Utils模块初始化器
 * 负责初始化工具类库
 * 使用androidx.startup.Initializer实现自动初始化
 */
class UtilsInitializer : Initializer<Unit> {

    override fun create(context: Context) {

        try {
            // 初始化Utils工具类
            Utils.init(context.applicationContext as Application)
            CrashUtils.init()
            LogUtils.getConfig()
                .setLogSwitch(AppUtils.isAppDebug())
                .setBorderSwitch(false)
                .setGlobalTag("LogUtils")
        } catch (e: Exception) {
            // 不抛出异常，避免阻塞应用启动
            e.printStackTrace()
        }
    }

    override fun dependencies(): List<Class<out Initializer<*>>> {
        return emptyList()
    }
}
