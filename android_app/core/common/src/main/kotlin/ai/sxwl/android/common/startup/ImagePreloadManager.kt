package ai.sxwl.android.common.startup

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

/**
 * 统一的图片预加载管理器
 * 整合设计模块的优化配置，提供高性能的图片预加载服务
 * 支持批量预加载、关键图像优先、设备装备等优化策略
 */
object ImagePreloadManager {

    private var isInitialized = false
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /** 初始化图片预加载管理器 */
    fun init(context: Context) {
        if (isInitialized) return

        try {
// 使用 core/design 模块中的高级配置
            AdvancedCoilConfig.initGlobalImageLoader()
            isInitialized = true
            LogUtils.i("ImagePreloadManager - 使用 core/design 模块配置初始化成功")
        } catch (e: Exception) {
            LogUtils.e("ImagePreloadManager - 初始化失败: ${e.message}")
        }
    }

    /**
     * 预加载代理的图片资源
     *
     * @param Agents 需要预加载的代理列表
     * @param maxConcurrent 最大并发预加载数量
     */
    suspend fun preloadAgentsImages(agents: List<AgentInfo>, maxConcurrent: Int = 5) {
        if (!isInitialized) {
            LogUtils.w("ImagePreloadManager - 未初始化，跳过预加载")
            return
        }

        if (agents.isEmpty()) {
            LogUtils.i("ImagePreloadManager - agents列表为空，跳过预加载")
            return
        }

        try {
            withContext(Dispatchers.IO) {
// 收集所有需要预加载的图片URL
                val imageUrls = collectImageUrls(agents)
                if (imageUrls.isNotEmpty()) {
// 使用全局ImageLoader进行预加载
                    preloadImagesToCoilCache(imageUrls, maxConcurrent)
                }
            }
        } catch (e: Exception) {
            LogUtils.e("ImagePreloadManager - 预加载异常: ${e.message}")
        }
    }

    /** 收集agents中的所有图片URL使用与ExploreCharacterCard的逻辑相同，确保URL一致性 */
    private fun collectImageUrls(agents: List<AgentInfo>): List<String> {
        val imageUrls = mutableSetOf<String>()

        agents.forEach { agent ->
// 使用与ExploreCharacterCard相同的逻辑获取图片URL
// 优先级：背景 -> 头像
            val imageUrl = agent.getAlbumImage()
            imageUrl?.takeIf { it.isNotBlank() }?.let { imageUrls.add(it) }
        }

        return imageUrls.toList()
    }

    /**
     * 预加载关键图片（前几屏的图片）
     *
     * @param Agents 需要预加载的代理列表
     * @param criticalCount 关键图片数量（前几屏）
     */
    suspend fun preloadCriticalImages(agents: List<AgentInfo>, criticalCount: Int = 10) {
        if (!isInitialized) {
            LogUtils.w("ImagePreloadManager - 未初始化，跳过关键图片预加载")
            return
        }

        val criticalAgents = agents.take(criticalCount)
        if (criticalAgents.isEmpty()) {
            LogUtils.i("ImagePreloadManager - 关键agents列表为空，跳过预加载")
            return
        }

        LogUtils.i("ImagePreloadManager - 开始预加载前 $criticalCount 个关键图片")

        try {
            withContext(Dispatchers.IO) {
                val imageUrls = collectImageUrls(criticalAgents)

                if (imageUrls.isNotEmpty()) {
// 使用全局ImageLoader进行关键图片预加载，提高梯度数
                    preloadImagesToCoilCache(imageUrls, maxConcurrent = 8)
                }
            }
            LogUtils.i("ImagePreloadManager - 关键图片预加载完成")
        } catch (e: Exception) {
            LogUtils.e("ImagePreloadManager - 关键图片预加载异常: ${e.message}")
        }
    }

    /**
     * 使用全局ImageLoader预加载图片到服务器
     *
     * @param imageUrls 需要预加载的图片URL列表
     * @param maxConcurrent 最大并发数
     */
    private suspend fun preloadImagesToCoilCache(imageUrls: List<String>, maxConcurrent: Int = 5) {
        coroutineScope {
// 分批处理，控制并发数
            imageUrls.chunked(maxConcurrent).forEach { batch ->
                val deferred = batch.map { imageUrl ->
                    async {
                        try {
// 使用全局ImageLoader和ImageLoaderUtils创建优化请求
                            val request = ImageLoaderUtils.createDeviceAdaptiveImageRequest(
                                context = Utils.getApp(),
                                imageUrl = imageUrl
                            )
// 执行预加载，图片会被存储到全局ImageLoader的内存和磁盘存储中
                            SingletonImageLoader.get(Utils.getApp()).execute(request)
                        } catch (e: Exception) {
                            LogUtils.w("ImagePreloadManager - 预加载失败: $imageUrl, 错误: ${e.message}")
                        }
                    }
                }
// 等待当前完成部分
                deferred.forEach { it.await() }
            }
        }
    }

    /**
     * 预加载单个图片到全局ImageLoader服务器
     * 使用设计模块的设备优化
     *
     * @param imageUrl 图片URL
     * @param size 目标尺寸，默认使用设备零售尺寸
     */
    suspend fun preloadSingleImage(imageUrl: String, size: Size = Size.ORIGINAL) {
        if (!isInitialized || imageUrl.isBlank()) {
            return
        }

        try {
            withContext(Dispatchers.IO) {
// 使用设计模块的设备优化
                val request = if (size == Size.ORIGINAL) {
                    ImageLoaderUtils.createDeviceAdaptiveImageRequest(
                        context = Utils.getApp(),
                        imageUrl = imageUrl
                    )
                } else {
                    ImageRequest.Builder(Utils.getApp())
                        .data(imageUrl)
                        .size(size)
                        .build()
                }
                SingletonImageLoader.get(Utils.getApp()).execute(request)
            }
        } catch (e: Exception) {
            LogUtils.w("ImagePreloadManager - 单图片预加载失败: $imageUrl, 错误: ${e.message}")
        }
    }

    /**
     * 预加载代理 相关图片
     * 利用丰富的优化，同时预收集资料和背景图片
     *
     * @param avatarUrl 头像 URL
     * @param backgroundUrl 背景图片URL
     */
    fun preloadAgentImages(avatarUrl: String?, backgroundUrl: String?) {
        if (!isInitialized) return

        scope.launch {
            try {
// 预装头像和背景图片
                val avatarJob = async {
                    avatarUrl?.let { preloadSingleImage(it, Size(120, 120)) }
                }
                val backgroundJob = async {
                    backgroundUrl?.let { preloadSingleImage(it, Size(400, 300)) }
                }
// 等待两个任务完成
                avatarJob.await()
                backgroundJob.await()

                LogUtils.d("ImagePreloadManager - 预加载 Agent 图片完成: avatar=$avatarUrl, background=$backgroundUrl")
            } catch (e: Exception) {
                LogUtils.e("ImagePreloadManager - 预加载 Agent 图片失败", e)
            }
        }
    }

    /**
     * 预加载用户头像
     * 使用头像优化的尺寸
     *
     * @param avatarUrl 头像 URL
     */
    fun preloadUserAvatar(avatarUrl: String?) {
        if (!isInitialized || avatarUrl.isNullOrBlank()) return

        scope.launch {
            try {
                preloadSingleImage(avatarUrl, Size(120, 120))
                LogUtils.d("ImagePreloadManager - 预加载用户头像: $avatarUrl")
            } catch (e: Exception) {
                LogUtils.e("ImagePreloadManager - 预加载用户头像失败", e)
            }
        }
    }

    /**
     * 预加载代理头像（指定尺寸）
     * 使用头像优化的请求配置
     *
     * @param avatarUrl 头像 URL
     * @param size 头像尺寸
     */
    fun preloadAgentAvatar(avatarUrl: String?, size: Int = 120) {
        if (!isInitialized || avatarUrl.isNullOrBlank()) return

        scope.launch {
            try {
// 使用设计模块的头像优化配置
                val request = ImageLoaderUtils.createAvatarImageRequest(
                    context = Utils.getApp(),
                    imageUrl = avatarUrl,
                    size = size
                )
                SingletonImageLoader.get(Utils.getApp()).execute(request)
                LogUtils.d("ImagePreloadManager - 预加载 Agent 头像: $avatarUrl (${size}x${size})")
            } catch (e: Exception) {
                LogUtils.e("ImagePreloadManager - 预加载 Agent 头像失败", e)
            }
        }
    }

    /**
     * 预加载代理背景图片
     * 使用背景图片优化的请求配置
     *
     * @param backgroundUrl 背景图片URL
     * @param width 宽度
     * @param height 高度
     */
    fun preloadAgentBackground(backgroundUrl: String?, width: Int = 400, height: Int = 300) {
        if (!isInitialized || backgroundUrl.isNullOrBlank()) return

        scope.launch {
            try {
// 使用设计部分的优化配置
                val request = ImageLoaderUtils.createThumbnailImageRequest(
                    context = Utils.getApp(),
                    imageUrl = backgroundUrl,
                    width = width,
                    height = height
                )
                SingletonImageLoader.get(Utils.getApp()).execute(request)
                LogUtils.d("ImagePreloadManager - 预加载 Agent 背景: $backgroundUrl (${width}x${height})")
            } catch (e: Exception) {
                LogUtils.e("ImagePreloadManager - 预加载 Agent 背景失败", e)
            }
        }
    }

    /**
     * 清理图片服务器
     * 使用设计模块的统一存储管理
     */
    fun clearImageCache() {
        if (!isInitialized) return

        try {
            AdvancedCoilConfig.clearImageCache(Utils.getApp())
            LogUtils.d("ImagePreloadManager - 清理图片缓存成功")
        } catch (e: Exception) {
            LogUtils.e("ImagePreloadManager - 清理图片缓存失败", e)
        }
    }

    /**
     * 获取图片存储大小
     * 使用设计模块的统一存储统计
     */
    fun getImageCacheSize(): String {
        return if (isInitialized) {
            val cacheSize = AdvancedCoilConfig.getImageCacheSize(Utils.getApp())
            AdvancedCoilConfig.formatCacheSize(cacheSize)
        } else {
            "0 B"
        }
    }

    /**
     * 预加载多张图片（批量优化）
     * 使用ARM控制和车辆设备优化
     *
     * @param imageUrls 图片URL列表
     * @param maxConcurrent 最大并发数
     */
    fun preloadImages(imageUrls: List<String>, maxConcurrent: Int = 5) {
        if (!isInitialized || imageUrls.isEmpty()) return

        scope.launch {
            try {
                withContext(Dispatchers.IO) {
// 分批处理，控制并发数
                    imageUrls.chunked(maxConcurrent).forEach { batch ->
                        val deferred = batch.map { imageUrl ->
                            async {
                                preloadSingleImage(imageUrl)
                            }
                        }
// 等待当前完成部分
                        deferred.forEach { it.await() }
                    }
                }
                LogUtils.d("ImagePreloadManager - 批量预加载完成: ${imageUrls.size} 张图片")
            } catch (e: Exception) {
                LogUtils.e("ImagePreloadManager - 批量预加载失败", e)
            }
        }
    }

    /** 获取预加载状态 */
    fun isInitialized(): Boolean {
        return isInitialized
    }
}
