package com.ai.inty.base

import ai.sxwl.android.utils.Utils
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.DefaultAlpha
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import coil3.ImageLoader
import coil3.compose.AsyncImage
import coil3.compose.AsyncImagePainter
import coil3.disk.DiskCache
import coil3.disk.directory
import coil3.memory.MemoryCache
import coil3.request.ImageRequest

fun initImageLoader() {
    try {
        val context = Utils.getApp()
        ImageLoader.Builder(context)
            .memoryCache {
                MemoryCache.Builder()
                    .maxSizePercent(context, 0.4) // 增加内存缓存到 40%
                    .build()
            }
            .diskCache {
                DiskCache.Builder()
                    .directory(context.cacheDir.resolve("image_cache"))
                    .maxSizePercent(0.05) // 增加磁盘缓存到 5%
                    .build()
            }
            .build()
    } catch (e: Exception) {
        // 如果初始化失败，使用默认配置
        val context = Utils.getApp()
        ImageLoader.Builder(context).build()
    }
}

@Composable
fun IntyImage(
    model: Any?,
    contentDescription: String? = null,
    modifier: Modifier = Modifier,
    placeholder: Painter? = null,
    error: Painter? = null,
    fallback: Painter? = error,
    onLoading: ((AsyncImagePainter.State.Loading) -> Unit)? = null,
    onSuccess: ((AsyncImagePainter.State.Success) -> Unit)? = null,
    onError: ((AsyncImagePainter.State.Error) -> Unit)? = null,
    alignment: Alignment = Alignment.TopCenter,
    contentScale: ContentScale = ContentScale.Crop,
    alpha: Float = DefaultAlpha,
    colorFilter: ColorFilter? = null,
    filterQuality: FilterQuality = DrawScope.DefaultFilterQuality,
) {
    val context = LocalContext.current
    val imageRequest =
        remember(model, context) {
            if (model is String) {
                ImageRequest.Builder(context).data(model).build()
            } else {
                model
            }
        }

    AsyncImage(
        model = imageRequest,
        contentDescription = contentDescription,
        modifier = modifier,
        placeholder = placeholder,
        error = error ?: placeholder,
        fallback = fallback,
        onLoading = onLoading,
        onSuccess = onSuccess,
        onError = onError,
        alignment = alignment,
        contentScale = contentScale,
        alpha = alpha,
        colorFilter = colorFilter,
        filterQuality = filterQuality,
    )
}

@Composable
fun IntyCircleImage(
    url: Any?,
    placeholderResID: Int,
    modifier: Modifier = Modifier,
    alignment: Alignment = Alignment.TopCenter,
    contentScale: ContentScale = ContentScale.Crop,
    alpha: Float = DefaultAlpha,
    colorFilter: ColorFilter? = null,
    filterQuality: FilterQuality = DrawScope.DefaultFilterQuality,
) {
    val context = LocalContext.current
    val imageRequest =
        remember(url, context) {
            if (url != null) {
                ImageRequest.Builder(context).data(url).build()
            } else {
                null
            }
        }

    IntyImage(
        modifier = modifier.clip(CircleShape),
        model = imageRequest,
        contentDescription = "",
        placeholder = painterResource(placeholderResID),
        error = painterResource(placeholderResID),
        alignment = alignment,
        contentScale = contentScale,
        alpha = alpha,
        colorFilter = colorFilter,
        filterQuality = filterQuality,
    )
}
