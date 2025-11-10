package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.design.ImageLoaderUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage

/** 全屏图片查看器 */
@Composable
internal fun FullScreenImageViewer(
    imageUrl: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    // 缩放、平移状态（不支持旋转）
    var scale by remember { mutableFloatStateOf(1f) }
    var offsetX by remember { mutableFloatStateOf(0f) }
    var offsetY by remember { mutableFloatStateOf(0f) }

    // 记录容器和图片的实际尺寸，用于计算平移边界
    var containerSize by remember { mutableStateOf(IntSize.Zero) }
    var imageSize by remember { mutableStateOf(IntSize.Zero) }

    // 计算平移边界约束
    // 当图片放大后，需要确保图片边缘不会离开屏幕边缘
    // 约束规则：图片边缘不能离开屏幕边缘
    fun calculateConstrainedOffset(
        currentOffset: Float,
        panChange: Float,
        containerSize: Float,
        imageSize: Float,
        currentScale: Float
    ): Float {
        if (currentScale <= 1f) return 0f // 缩放为1时，不允许平移

        // 计算放大后图片的实际尺寸（原始显示尺寸 * 缩放比例）
        val scaledImageSize = imageSize * currentScale

        // 计算可平移的范围
        // 图片中心在容器中心，所以可平移的最大范围是图片超出容器的部分的一半
        // 如果缩放后图片小于容器，则不可平移
        val maxOffset = if (scaledImageSize > containerSize) {
            (scaledImageSize - containerSize) / 2f
        } else {
            0f
        }

        // 计算新的偏移量
        val newOffset = currentOffset + panChange

        // 约束在边界内：[-maxOffset, maxOffset]
        return newOffset.coerceIn(-maxOffset, maxOffset)
    }

    // 使用transformable手势处理缩放和平移（不允许旋转）
    // 注意：zoomChange 是相对于上一次调用的变化量，不是累积值
    val transformableState = rememberTransformableState(
        onTransformation = { zoomChange: Float, panChange: Offset, rotationChange: Float ->
            // 缩放：最小1倍，最大5倍（不可缩小）
            val newScale = (scale * zoomChange).coerceIn(1f, 5f)
            scale = newScale

            // 平移：只在缩放大于1倍时允许平移，并应用边界约束
            if (newScale > 1f && containerSize.width > 0 && containerSize.height > 0 && imageSize.width > 0 && imageSize.height > 0) {
                // 计算约束后的平移偏移
                offsetX = calculateConstrainedOffset(
                    currentOffset = offsetX,
                    panChange = panChange.x,
                    containerSize = containerSize.width.toFloat(),
                    imageSize = imageSize.width.toFloat(),
                    currentScale = newScale
                )
                offsetY = calculateConstrainedOffset(
                    currentOffset = offsetY,
                    panChange = panChange.y,
                    containerSize = containerSize.height.toFloat(),
                    imageSize = imageSize.height.toFloat(),
                    currentScale = newScale
                )
            } else {
                // 如果缩放回到1倍，重置平移
                offsetX = 0f
                offsetY = 0f
            }

            // 忽略旋转（rotationChange）
        }
    )

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.95f))
            .onGloballyPositioned { coordinates ->
                containerSize = coordinates.size
            },
        contentAlignment = Alignment.Center,
    ) {
        // 图片
        AsyncImage(
            modifier = Modifier
                .fillMaxSize()
                .onGloballyPositioned { coordinates ->
                    // 记录图片的实际显示尺寸（使用ContentScale.Fit后的尺寸）
                    imageSize = coordinates.size
                }
                .graphicsLayer(
                    scaleX = scale,
                    scaleY = scale,
                    translationX = offsetX,
                    translationY = offsetY,
                )
                .transformable(state = transformableState),
            model = ImageLoaderUtils.createDeviceAdaptiveImageRequest(
                context = context,
                imageUrl = getCdnImageUrl(imageUrl, width = 1920, quality = 85),
                maxWidth = 1920,
                maxHeight = 1920,
            ),
            contentDescription = "Full screen image",
            contentScale = ContentScale.Fit,
            alignment = Alignment.Center,
        )

        // 左上角关闭按钮（使用X符号）
        IconButton(
            onClick = { onDismiss() },
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(16.dp),
        ) {
            androidx.compose.material3.Text(
                text = "✕",
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}
