package ai.sxwl.android.common.startup

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.AdvancedCoilConfig
import ai.sxwl.android.design.ImageLoaderUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import coil3.SingletonImageLoader
import coil3.request.ImageRequest
import coil3.size.Size
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** 统一的图片预加载管理器 整合 design 模块的优化配置，提供高性能的图片预加载服务 支持批量预加载、关键图片优先、设备适配等优化策略 */
object ImagePreloadManager {

    private var isInitialized = false
    private var applicationContext: Context? = null
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /** 初始化图片预加载管理器 */
    fun init(context: Context) {
        if (isInitialized) return

        try {
            // 保存 applicationContext 用于后续预加载
            applicationContext = context.applicationContext

            // 使用 core/design 模块中的高级配置
            AdvancedCoilConfig.initGlobalImageLoader()
            isInitialized = true
        } catch (e: Exception) {
            LogUtils.e("ImagePreloadManager - 初始化失败: ${e.message}")
        }
    }

    /**
     * 预加载agents的图片资源
     * 包括：ExploreCharacterCard使用的图片（getAlbumImage）和AgentBackground使用的静态背景图（getOriginShowImage）
     *
     * @param agents 需要预加载的agents列表
     * @param maxConcurrent 最大并发预加载数量
     */
    suspend fun preloadAgentsImages(agents: List<AgentInfo>, maxConcurrent: Int = 5) {
        if (!isInitialized) {
            LogUtils.w("ImagePreloadManager - 未初始化，跳过预加载")
            return
        }

        if (agents.isEmpty()) {
            return
        }

        try {
            withContext(Dispatchers.IO) {
                // 收集所有需要预加载的图片URL
                val albumImageUrls = collectImageUrls(agents) // ExploreCharacterCard使用的图片
                val staticBackgroundUrls =
                    collectStaticBackgroundImageUrls(agents) // AgentBackground使用的静态背景图（使用固定参数）

                // 合并所有URL并去重
                val allImageUrls = (albumImageUrls + staticBackgroundUrls).distinct()

                if (allImageUrls.isNotEmpty()) {
                    // 使用全局ImageLoader进行预加载
                    preloadImagesToCoilCache(allImageUrls, maxConcurrent)
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ImagePreloadManager - 预加载异常: ${e.message}")
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
     * 收集agents中的静态背景图URL（用于AgentBackground组件） 使用与AgentBackground相同的逻辑，确保URL一致性 使用固定参数（width=1080,
     * quality=75）确保预加载和实际使用的 URL 完全一致
     *
     * @param agents agents列表
     * @return 静态背景图URL列表（已通过CDN优化）
     */
    private fun collectStaticBackgroundImageUrls(agents: List<AgentInfo>): List<String> {
        val imageUrls = mutableSetOf<String>()

        // 使用固定 CDN 参数，与 AgentBackground 和 AnimatedBackground 保持一致
        // 1080px 宽度适用于大多数 Android 设备，80% 质量在清晰度和文件大小之间取得最佳平衡
        val CDN_STATIC_BACKGROUND_WIDTH = 1080
        val CDN_IMAGE_QUALITY = 80

        agents.forEach { agent ->
            // 使用与AgentBackground相同的逻辑获取静态背景图URL
            // getOriginShowImage() 返回原始URL，需要经过CDN优化
            val originImageUrl = agent.getOriginShowImage()
            if (originImageUrl?.isNotBlank() == true) {
                // 使用固定 CDN 参数，确保与 AgentBackground 和 AnimatedBackground 的 URL 完全一致
                val optimizedUrl =
                    getCdnImageUrl(
                        originImageUrl,
                        width = CDN_STATIC_BACKGROUND_WIDTH,
                        quality = CDN_IMAGE_QUALITY,
                    ) ?: originImageUrl
                imageUrls.add(optimizedUrl)
            }
        }

        return imageUrls.toList()
    }

    /**
     * 预加载关键图片（前几屏的图片） 包括：ExploreCharacterCard使用的图片和AgentBackground使用的静态背景图
     *
     * @param agents 需要预加载的agents列表
     * @param criticalCount 关键图片数量（前几屏）
     */
    suspend fun preloadCriticalImages(agents: List<AgentInfo>, criticalCount: Int = 10) {
        if (!isInitialized) {
            LogUtils.w("ImagePreloadManager - 未初始化，跳过关键图片预加载")
            return
        }

        val criticalAgents = agents.take(criticalCount)
        if (criticalAgents.isEmpty()) {
            return
        }

        try {
            withContext(Dispatchers.IO) {
                val albumImageUrls = collectImageUrls(criticalAgents)
                val staticBackgroundUrls =
                    collectStaticBackgroundImageUrls(criticalAgents) // 使用固定参数

                // 合并所有URL并去重
                val allImageUrls = (albumImageUrls + staticBackgroundUrls).distinct()

                if (allImageUrls.isNotEmpty()) {
                    // 使用全局ImageLoader进行关键图片预加载，提高并发数
                    preloadImagesToCoilCache(allImageUrls, maxConcurrent = 8)
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ImagePreloadManager - 关键图片预加载异常: ${e.message}")
        }
    }

    /**
     * 使用全局ImageLoader预加载图片到缓存
     *
     * @param imageUrls 需要预加载的图片URL列表
     * @param maxConcurrent 最大并发数
     */
    private suspend fun preloadImagesToCoilCache(imageUrls: List<String>, maxConcurrent: Int = 5) {
        coroutineScope {
            // 分批处理，控制并发数
            imageUrls.chunked(maxConcurrent).forEach { batch ->
                val deferred =
                    batch.map { imageUrl ->
                        async {
                            try {
                                // 使用全局ImageLoader和ImageLoaderUtils创建优化请求
                                val request =
                                    ImageLoaderUtils.createDeviceAdaptiveImageRequest(
                                        context = Utils.getApp(),
                                        imageUrl = imageUrl,
                                    )
                                // 执行预加载，图片会被缓存到全局ImageLoader的内存和磁盘缓存中
                                SingletonImageLoader.get(Utils.getApp()).execute(request)
                            } catch (e: Exception) {
                                LogUtils.w(
                                    "ImagePreloadManager - 预加载失败: $imageUrl, 错误: ${e.message}"
                                )
                            }
                        }
                    }

                // 等待当前批次完成
                deferred.forEach { it.await() }
            }
        }
    }
}
