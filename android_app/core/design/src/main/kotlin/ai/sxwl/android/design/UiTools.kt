package ai.sxwl.android.design

import android.os.Build
import android.os.Build.VERSION.SDK_INT
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.ui.platform.LocalInspectionMode
import androidx.compose.ui.platform.LocalView
import coil3.ImageLoader
import coil3.SingletonImageLoader
import coil3.disk.DiskCache
import coil3.disk.directory
import coil3.gif.AnimatedImageDecoder
import coil3.gif.GifDecoder
import coil3.memory.MemoryCache
import coil3.request.crossfade
import coil3.svg.SvgDecoder
import coil3.video.VideoFrameDecoder

// 用于标记，当前代码适用于IDE预览，还是实际代码环境
@Stable
val isInPreview
    @Composable get() = LocalInspectionMode.current

@Stable
val isInEditMode: Boolean
    @Composable get() = LocalView.current.isInEditMode

/** 初始化配置coil的imageLoader 根据Coil 3.x官方文档优化配置，支持设备适配的图片压缩 参考：https://coil-kt.github.io/coil/ */
fun initCoilImageLoader() {
    SingletonImageLoader.setSafe { context ->
        ImageLoader.Builder(context)
            .memoryCache {
                MemoryCache.Builder()
                    .maxSizePercent(context, 0.4) // 增加内存缓存到40%
                    .build()
            }
            .diskCache {
                DiskCache.Builder()
                    .directory(context.cacheDir.resolve("image_cache"))
                    .maxSizePercent(0.05) // 增加磁盘缓存到5%
                    .build()
            }
            .components {
                add(SvgDecoder.Factory())
                if (SDK_INT >= Build.VERSION_CODES.P) {
                    add(AnimatedImageDecoder.Factory())
                } else {
                    add(GifDecoder.Factory())
                }
                add(VideoFrameDecoder.Factory())
            }
            .crossfade(true)
            .crossfade(300) // 300ms的交叉淡入淡出
            .build()
    }
}
