package ai.sxwl.android.design

import android.content.Context
import androidx.startup.Initializer

/**
 * 设计初始化模块器
 * 负责初始化图片加载库等设计相关组件
 * 使用androidx。启动。初始化器实现自动初始化
 */
class DesignInitializer : Initializer<Unit> {

    override fun create(context: Context) {
        try {
// 初始化图片加载库 - 使用高级配置
            AdvancedCoilConfig.initGlobalImageLoader()
// 保留原有的初始化方法作为备用
            initCoilImageLoader()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun dependencies(): List<Class<out Initializer<*>>> {
// 依赖Utils模块的初始化（如果Utils模块也有Initializer）
        return emptyList()
    }
}
