package com.ai.inty.utils

import android.content.Context
import com.ai.inty.beans.AgentInfo
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * 图片预加载管理器
 * 负责在启动时预加载agents的图片资源，优化Explore页面渲染体验
 */
object ImagePreloadManager {

    private var isInitialized = false

    /**
     * 初始化图片预加载管理器
     */
    fun init(context: Context) {
        if (isInitialized) return

        isInitialized = true
        EasyLog.log("ImagePreloadManager - 初始化完成")
    }

    /**
     * 预加载agents的图片资源
     * @param agents 需要预加载的agents列表
     * @param maxConcurrent 最大并发预加载数量
     */
    suspend fun preloadAgentsImages(
        agents: List<AgentInfo>,
        maxConcurrent: Int = 5
    ) {
        if (!isInitialized) {
            EasyLog.log("ImagePreloadManager - 未初始化，跳过预加载", EasyLog.WARN)
            return
        }

        if (agents.isEmpty()) {
            EasyLog.log("ImagePreloadManager - agents列表为空，跳过预加载")
            return
        }

        EasyLog.log("ImagePreloadManager - 开始预加载 ${agents.size} 个agents的图片资源")

        try {
            withContext(Dispatchers.IO) {
                // 收集所有需要预加载的图片URL
                val imageUrls = collectImageUrls(agents)
                EasyLog.log("ImagePreloadManager - 收集到 ${imageUrls.size} 个图片URL")

                if (imageUrls.isNotEmpty()) {
                    // 使用批量预加载方法，提高效率

                    EasyLog.log("ImagePreloadManager - 批量预加载图片尺寸完成")

                    // 图片尺寸预加载完成后，更新卡片高度
                    agents.forEach { agent ->

                    }
                }
            }

            EasyLog.log("ImagePreloadManager - 所有图片预加载完成")

        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 预加载异常: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 收集agents中的所有图片URL
     * 使用与ExploreCharacterCard相同的逻辑，确保URL一致性
     */
    private fun collectImageUrls(agents: List<AgentInfo>): List<String> {
        val imageUrls = mutableSetOf<String>()

        agents.forEach { agent ->
            // 使用与ExploreCharacterCard相同的逻辑获取图片URL
            // 优先级：background -> avatar
            val imageUrl = agent.getLargeBackground()
            imageUrl?.takeIf { it.isNotBlank() }?.let { imageUrls.add(it) }
        }

        return imageUrls.toList()
    }

    /**
     * 预加载关键图片（前几屏的图片）
     * @param agents 需要预加载的agents列表
     * @param criticalCount 关键图片数量（前几屏）
     */
    suspend fun preloadCriticalImages(
        agents: List<AgentInfo>,
        criticalCount: Int = 10
    ) {
        if (!isInitialized) {
            EasyLog.log("ImagePreloadManager - 未初始化，跳过关键图片预加载", EasyLog.WARN)
            return
        }

        val criticalAgents = agents.take(criticalCount)
        if (criticalAgents.isEmpty()) {
            EasyLog.log("ImagePreloadManager - 关键agents列表为空，跳过预加载")
            return
        }

        EasyLog.log("ImagePreloadManager - 开始预加载前 $criticalCount 个关键图片")

        try {
            withContext(Dispatchers.IO) {
                val imageUrls = collectImageUrls(criticalAgents)

                if (imageUrls.isNotEmpty()) {
                    // 使用批量预加载方法，优先预加载关键图片

                    EasyLog.log("ImagePreloadManager - 关键图片批量预加载完成")

                }
            }

            EasyLog.log("ImagePreloadManager - 关键图片预加载完成")

        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 关键图片预加载异常: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 获取预加载状态
     */
    fun isInitialized(): Boolean {
        return isInitialized
    }

}

/**
 * 使用cdn自动裁剪图片的示例
 * 原图url是 https://images.sxwl.dev/inty-static/backgrounds/user-01JWZ34Y4D1C92GD86A5R6EWYJ/b4cb39bfe2fc4a92aec3bd406cc2ebaa/1758095758195/sample_0.jpg
 * 拼接/cdn-cgi/image/quality=75/后 https://images.sxwl.dev/cdn-cgi/image/quality=75/inty-static/backgrounds/user-01JWZ34Y4D1C92GD86A5R6EWYJ/b4cb39bfe2fc4a92aec3bd406cc2ebaa/1758095758195/sample_0.jpg
 * 也可以是/cdn-cgi/image/width=720,quality=75,format=webp/这样（目前webp转化不生效）
 */

/**
 * 获取cdn裁剪图片的url
 * @param originUrl 原始图片url
 * @param width 需要的宽度
 * @param quality 需要的图片质量 默认75%的原图质量
 * @return 业务cdn处理后的url，也可能null，也可能不处理
 */
fun getCdnImageUrl(originUrl: String?, width: Int = 1080, quality: Int = 75): String? {
    originUrl ?: return null
    return when {
        originUrl.contains("/cdn-cgi/image/") -> {
            originUrl
        }

        originUrl.contains("/inty-static") -> {
            originUrl.replace(
                "/inty-static",
                "/cdn-cgi/image/width=$width,quality=$quality/inty-static",
                ignoreCase = true
            )
        }

        else -> originUrl
    }
}
