package com.ai.inty.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import com.ai.inty.base.IntyImage
import com.ai.inty.beans.AgentInfo
import kotlin.math.abs
import kotlin.math.roundToInt

/** 通用角色背景组件 可用于聊天页面、角色主页等需要角色背景的地方 */
@Composable
fun AgentBackground(
    agentInfo: AgentInfo?,
    modifier: Modifier = Modifier,
    showGradients: Boolean = true,
) {
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current

    var imageWidthDp by remember { mutableIntStateOf(configuration.screenWidthDp) }
    var imageHeightDp by remember { mutableIntStateOf(configuration.screenHeightDp) }

    if (configuration.screenWidthDp > imageWidthDp) {
        imageWidthDp = configuration.screenWidthDp
    }
    if (configuration.screenHeightDp > imageHeightDp) {
        imageHeightDp = configuration.screenHeightDp
    }

    // 状态来存储图片尺寸
    var imageWidth by remember { mutableStateOf<Int?>(null) }
    var imageHeight by remember { mutableStateOf<Int?>(null) }

    // 计算最佳的 ContentScale
    val currentImageWidth = imageWidth
    val currentImageHeight = imageHeight
    val optimalContentScale =
        if (
            currentImageWidth != null &&
                currentImageHeight != null &&
                currentImageWidth > 0 &&
                currentImageHeight > 0
        ) {
            calculateOptimalContentScale(
                containerWidth = imageWidthDp,
                containerHeight = imageHeightDp,
                imageWidth = currentImageWidth,
                imageHeight = currentImageHeight,
            )
        } else {
            ContentScale.Crop // 默认值，当图片尺寸未知时
        }

    Box(modifier = modifier) {
        Column(
            modifier =
                Modifier.fillMaxSize().verticalScroll(rememberScrollState(), false).onSizeChanged {
                    val newHeight = with(density) { it.height.toDp().value.roundToInt() }
                    if (newHeight > imageHeightDp) {
                        imageHeightDp = newHeight
                    }
                }
        ) {
            IntyImage(
                modifier = Modifier.size(imageWidthDp.dp, imageHeightDp.dp),
                model = agentInfo?.getAlbumImage(),
                alignment = Alignment.TopCenter,
                contentScale = optimalContentScale,
                onSuccess = { state ->
                    // 当图片加载成功时，获取图片尺寸
                    val drawable = state.painter
                    imageWidth = drawable.intrinsicSize.width.toInt()
                    imageHeight = drawable.intrinsicSize.height.toInt()
                },
            )
        }

        // 渐变遮罩 - 仅在需要时显示
        if (showGradients) {
            // 顶部渐变遮罩 - 固定位置
            val colors = listOf(Color(0xFF000000), Color(0x00000000))
            Box(
                modifier =
                    Modifier.fillMaxWidth()
                        .height(120.dp)
                        .background(brush = Brush.verticalGradient(colors))
            )

            // 底部渐变遮罩 - 固定位置
            val bottomColors = listOf(Color(0x001C1523), Color(0xFF1C1523))
            Box(
                modifier =
                    Modifier.fillMaxWidth()
                        .height(300.dp)
                        .background(brush = Brush.verticalGradient(bottomColors))
                        .align(Alignment.BottomCenter)
            )
        }
    }
}

/**
 * 根据容器和图片的宽高比计算最佳的 ContentScale 只支持人像模式屏幕显示，即尽量不留左右两侧空白。 当容器高宽比大于图片高宽比时，使用 FillHeight 填充高度，否则使用
 * FillWidth 填充宽度。
 *
 * @param containerWidth 容器宽度（dp）
 * @param containerHeight 容器高度（dp）
 * @param imageWidth 图片宽度（像素）
 * @param imageHeight 图片高度（像素）
 * @return 最佳的 ContentScale
 */
fun calculateOptimalContentScale(
    containerWidth: Int,
    containerHeight: Int,
    imageWidth: Int,
    imageHeight: Int,
): ContentScale {
    val screenAspectRatio = containerWidth.toFloat() / containerHeight.toFloat()
    val imageAspectRatio = imageWidth.toFloat() / imageHeight.toFloat()
    return when {
        // 如果屏幕和图片宽高比非常接近（差异小于5%），使用 Fit 显示完整图片
        // 例如：屏幕 9:16 (0.5625)，图片 9:16 (0.5625) → 使用 Fit
        abs(screenAspectRatio - imageAspectRatio) / imageAspectRatio < 0.05f -> ContentScale.Fit

        // 如果屏幕比图片更宽（屏幕宽高比 > 图片宽高比），图片相对较窄，使用 FillWidth
        // 例如：屏幕 16:9 (1.78)，图片 9:16 (0.5625) → 使用 FillWidth
        screenAspectRatio > imageAspectRatio -> ContentScale.FillWidth

        // 如果屏幕比图片更窄（屏幕宽高比 < 图片宽高比），图片相对较宽，使用 FillHeight
        // 例如：屏幕 9:16 (0.5625)，图片 16:9 (1.78) → 使用 FillHeight
        else -> ContentScale.FillHeight
    }
}
