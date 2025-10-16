package com.ai.inty.utils

import android.content.Context
import coil3.ImageLoader
import coil3.disk.directory
import coil3.request.ImageRequest
import com.ai.inty.beans.AgentInfo
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext

/** 图片预加载管理器 负责在启动时预加载agents的图片资源，优化Explore页面渲染体验 */
object ImagePreloadManager {

    private var isInitialized = false
    private var imageLoader: ImageLoader? = null

    /** 初始化图片预加载管理器 */
    fun init(context: Context) {
        if (isInitialized) return

        try {
            // 获取全局ImageLoader实例
            imageLoader =
                ImageLoader.Builder(context)
                    .memoryCache {
                        coil3.memory.MemoryCache.Builder()
                            .maxSizePercent(context, 0.4) // 40% 内存缓存
                            .build()
                    }
                    .diskCache {
                        coil3.disk.DiskCache.Builder()
                            .directory(context.cacheDir.resolve("image_cache"))
                            .maxSizePercent(0.05) // 5% 磁盘缓存
                            .build()
                    }
                    .build()

            isInitialized = true
            EasyLog.log("ImagePreloadManager - 初始化完成")
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 初始化失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 预加载agents的图片资源
     *
     * @param agents 需要预加载的agents列表
     * @param maxConcurrent 最大并发预加载数量
     */
    suspend fun preloadAgentsImages(agents: List<AgentInfo>, maxConcurrent: Int = 5) {
        if (!isInitialized || imageLoader == null) {
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
                    // 使用Coil进行真正的图片预加载缓存
                    preloadImagesToCoilCache(imageUrls, maxConcurrent)
                    EasyLog.log("ImagePreloadManager - 批量预加载图片到Coil缓存完成")
                }
            }

            EasyLog.log("ImagePreloadManager - 所有图片预加载完成")
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 预加载异常: ${e.message}", EasyLog.ERROR)
        }
    }

    /** 收集agents中的所有图片URL 使用与ExploreCharacterCard相同的逻辑，确保URL一致性 */
    private fun collectImageUrls(agents: List<AgentInfo>): List<String> {
        val imageUrls = mutableSetOf<String>()

        agents.forEach { agent ->
            // 使用与ExploreCharacterCard相同的逻辑获取图片URL
            // 优先级：background -> avatar
            val imageUrl = agent.getAlbumImage()
            imageUrl?.takeIf { it.isNotBlank() }?.let { imageUrls.add(it) }
        }

        return imageUrls.toList()
    }

    /**
     * 预加载关键图片（前几屏的图片）
     *
     * @param agents 需要预加载的agents列表
     * @param criticalCount 关键图片数量（前几屏）
     */
    suspend fun preloadCriticalImages(agents: List<AgentInfo>, criticalCount: Int = 10) {
        if (!isInitialized || imageLoader == null) {
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
                    // 使用Coil进行关键图片预加载缓存，提高并发数
                    preloadImagesToCoilCache(imageUrls, maxConcurrent = 8)
                    EasyLog.log("ImagePreloadManager - 关键图片批量预加载到Coil缓存完成")
                }
            }

            EasyLog.log("ImagePreloadManager - 关键图片预加载完成")
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 关键图片预加载异常: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 使用Coil预加载图片到缓存
     *
     * @param imageUrls 需要预加载的图片URL列表
     * @param maxConcurrent 最大并发数
     */
    private suspend fun preloadImagesToCoilCache(imageUrls: List<String>, maxConcurrent: Int = 5) {
        val loader = imageLoader ?: return

        coroutineScope {
            // 分批处理，控制并发数
            imageUrls.chunked(maxConcurrent).forEach { batch ->
                val deferred =
                    batch.map { imageUrl ->
                        async {
                            try {
                                val request =
                                    ImageRequest.Builder(AppEnv.context).data(imageUrl).build()

                                // 执行预加载，图片会被缓存到Coil的内存和磁盘缓存中
                                loader.execute(request)
                                EasyLog.log("ImagePreloadManager - 预加载成功: $imageUrl", EasyLog.DEBUG)
                            } catch (e: Exception) {
                                EasyLog.log(
                                    "ImagePreloadManager - 预加载失败: $imageUrl, 错误: ${e.message}",
                                    EasyLog.WARN,
                                )
                            }
                        }
                    }

                // 等待当前批次完成
                deferred.forEach { it.await() }
            }
        }
    }

    /**
     * 预加载单个图片到Coil缓存
     *
     * @param imageUrl 图片URL
     */
    suspend fun preloadSingleImage(imageUrl: String) {
        if (!isInitialized || imageLoader == null || imageUrl.isBlank()) {
            return
        }

        try {
            withContext(Dispatchers.IO) {
                val loader = imageLoader!!
                val request = ImageRequest.Builder(AppEnv.context).data(imageUrl).build()

                loader.execute(request)
                EasyLog.log("ImagePreloadManager - 单图片预加载成功: $imageUrl", EasyLog.DEBUG)
            }
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 单图片预加载失败: $imageUrl, 错误: ${e.message}", EasyLog.WARN)
        }
    }

    /** 获取预加载状态 */
    fun isInitialized(): Boolean {
        return isInitialized
    }
}




