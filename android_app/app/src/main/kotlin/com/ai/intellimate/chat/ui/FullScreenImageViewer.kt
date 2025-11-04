package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest

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

    // 动画缩放值
    val animatedScale by animateFloatAsState(
        targetValue = scale,
        animationSpec = tween(200),
        label = "scale"
    )

    // 使用transformable手势处理缩放和平移（不允许旋转）
    val transformableState = rememberTransformableState(
        onTransformation = { zoomChange: Float, panChange: Offset, rotationChange: Float ->
            // 缩放：最小1倍，最大5倍（不能缩小）
            val newScale = (scale * zoomChange).coerceIn(1f, 5f)
            scale = newScale
            // 平移：只在缩放大于1倍时允许平移
            if (newScale > 1f) {
                offsetX += panChange.x
                offsetY += panChange.y
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
            .background(Color.Black.copy(alpha = 0.95f)),
        contentAlignment = Alignment.Center,
    ) {
        // 图片
        AsyncImage(
            modifier = Modifier
                .fillMaxSize()
                .graphicsLayer(
                    scaleX = animatedScale,
                    scaleY = animatedScale,
                    translationX = offsetX,
                    translationY = offsetY,
                )
                .transformable(state = transformableState),
            model = ImageRequest.Builder(context)
                .data(getCdnImageUrl(imageUrl, width = 1920, quality = 85))
                .build(),
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
