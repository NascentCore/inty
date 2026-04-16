package ai.sxwl.android.utils

import android.app.Application
import android.content.Context
import android.util.Log
import androidx.startup.Initializer

/** Utils模块初始化器 负责初始化工具类库 使用androidx.startup.Initializer实现自动初始化 */
class UtilsInitializer : Initializer<Unit> {

    override fun create(context: Context) {
        try {
            // 安全的类型转换
            val app = context.applicationContext as? Application
            if (app == null) {
                Log.e("UtilsInitializer", "Application context is null")
                return
            }

            // 初始化Utils工具类
            Utils.init(app)
            LogUtils.getConfig()
                .setLogSwitch(AppUtils.isAppDebug())
                .setBorderSwitch(false)
                .setGlobalTag("LogUtils")
        } catch (e: ClassCastException) {
            Log.e("UtilsInitializer", "Context is not Application", e)
        } catch (e: Exception) {
            Log.e("UtilsInitializer", "Utils initialization failed", e)
            // 可以考虑上报崩溃信息到崩溃收集服务
        }
    }

    override fun dependencies(): List<Class<out Initializer<*>>> {
        return emptyList()
    }
}
