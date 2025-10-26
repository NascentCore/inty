package ai.sxwl.android.design

import android.content.Context
import android.os.Build
import coil3.ImageLoader
import coil3.SingletonImageLoader
import coil3.disk.DiskCache
import coil3.disk.directory
import coil3.gif.AnimatedImageDecoder
import coil3.gif.GifDecoder
import coil3.memory.MemoryCache
import coil3.network.okhttp.OkHttpNetworkFetcherFactory
import coil3.request.crossfade
import coil3.svg.SvgDecoder
import coil3.video.VideoFrameDecoder
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

/** 高级Coil配置类 根据Coil 3.x官方文档：https://coil-kt.github.io/coil/network/ 提供完整的网络支持和缓存策略 */
object AdvancedCoilConfig {
    /**
     * 创建优化的ImageLoader，支持设备适配的图片压缩 根据Coil 3.x官方文档：https://coil-kt.github.io/coil/
     *
     * @param context 上下文
     * @return 配置好的ImageLoader
     */
    fun createOptimizedImageLoader(context: Context): ImageLoader {
        // 创建专门用于图片加载的OkHttpClient
        val imageHttpClient = createImageHttpClient()

        return ImageLoader.Builder(context)
            .memoryCache {
                MemoryCache.Builder()
                    .maxSizePercent(context, 0.4) // 40%内存缓存
                    .build()
            }
            .diskCache {
                DiskCache.Builder()
                    .directory(context.cacheDir.resolve("image_cache"))
                    .maxSizePercent(0.05) // 5%磁盘缓存
                    .build()
            }
            .components {
                // 添加各种解码器支持
                add(SvgDecoder.Factory())
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    add(AnimatedImageDecoder.Factory())
                } else {
                    add(GifDecoder.Factory())
                }
                add(VideoFrameDecoder.Factory())
                add(OkHttpNetworkFetcherFactory(callFactory = { imageHttpClient }))
            }
            .crossfade(true)
            .crossfade(300) // 300ms交叉淡入淡出
            .build()
    }

    /** 创建专门用于图片加载的OkHttpClient 根据官方文档优化网络配置，处理连接重置问题 */
    private fun createImageHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
            .connectTimeout(60, TimeUnit.SECONDS) // 连接超时60秒
            .readTimeout(60, TimeUnit.SECONDS) // 读取超时60秒
            .writeTimeout(60, TimeUnit.SECONDS) // 写入超时60秒
            .retryOnConnectionFailure(true) // 连接失败时重试
            .build()
    }

    /** 初始化全局ImageLoader 使用优化的配置 */
    fun initGlobalImageLoader() {
        SingletonImageLoader.setSafe { context -> createOptimizedImageLoader(context) }
    }

    /**
     * 获取图片缓存大小（字节）
     *
     * @param context 上下文
     * @return 缓存大小
     */
    fun getImageCacheSize(context: Context): Long {
        return try {
            val cacheDir = context.cacheDir.resolve("image_cache")
            if (cacheDir.exists()) {
                cacheDir.walkTopDown().filter { it.isFile }.map { it.length() }.sum()
            } else {
                0L
            }
        } catch (e: Exception) {
            0L
        }
    }

    /**
     * 清除图片缓存
     *
     * @param context 上下文
     */
    fun clearImageCache(context: Context) {
        try {
            val cacheDir = context.cacheDir.resolve("image_cache")
            if (cacheDir.exists()) {
                cacheDir.deleteRecursively()
            }
        } catch (e: Exception) {
            // 忽略清除缓存时的错误
        }
    }

    /**
     * 格式化缓存大小
     *
     * @param bytes 字节数
     * @return 格式化的字符串
     */
    fun formatCacheSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
            else -> "${bytes / (1024 * 1024 * 1024)} GB"
        }
    }
}
