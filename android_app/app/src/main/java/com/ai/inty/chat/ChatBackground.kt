package com.ai.inty.chat

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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.inty.base.IntyImage
import com.ai.inty.beans.AgentInfo
import com.ai.inty.utils.getChatBackground
import com.ai.inty.utils.calculateOptimalContentScale
import kotlin.math.roundToInt
import coil3.compose.AsyncImagePainter


@Composable
fun ChatBackground(
    agentInfo: AgentInfo?,
    modifier: Modifier = Modifier,
) {
    AgentBackground(
        agentInfo = agentInfo,
        modifier = modifier,
        showGradients = true
    )
}

/**
 * 角色背景
 * 用于聊天页面、角色主页等将角色形象作为背景展示前景其他内容。
 * 前景内容包括：
 * 聊天页面的消息（主题）、输入（底部）、top bar（左上方）、设置（右上方）
 * 角色主页的简介、开场白等
 */
@Composable
fun AgentBackground(
    agentInfo: AgentInfo?,
    modifier: Modifier = Modifier,
    showGradients: Boolean = true,
) {
    /* 工作机制：
     * 获得当前显示区域的大小
     * ？获取图片尺寸，如果图片尚未加载，则显示 placeholder
     * 获取图片后，根据图片尺寸，决定最佳 scale
     */
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current
    // TODO: 这里是否应该查询 chat 界面显示范围的大小，而非 window
    val containerSize = LocalWindowInfo.current.containerSize

    var screenWidth by remember {
        mutableIntStateOf(containerSize.width)
    }
    var screenHeight by remember {
        mutableIntStateOf(containerSize.height)
    }

    screenWidth = containerSize.width
    screenHeight =  containerSize.height

    // 状态来存储图片尺寸
    var imageWidth by remember { mutableStateOf<Int?>(null) }
    var imageHeight by remember { mutableStateOf<Int?>(null) }
    
    val optimalContentScale = calculateOptimalContentScale(
        containerWidth = screenWidth,
        containerHeight = screenHeight,
        imageWidth = imageWidth,
        imageHeight = imageHeight
    )

    Box(modifier = modifier) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState(), false)
                .onSizeChanged {
                    screenWidth = with(density) {
                        it.width.toDp().value.roundToInt()
                    }
                    screenHeight = with(density) {
                        it.height.toDp().value.roundToInt()
                    }
                }
        ) {
            IntyImage(
                modifier = Modifier
                    .size(screenWidth.dp, screenHeight.dp),
                model = agentInfo?.getChatBackground(),
                alignment = Alignment.TopCenter,
                contentScale = optimalContentScale,
                onSuccess = { state ->
                    // 当图片加载成功时，获取图片尺寸
                    val drawable = state.painter
                    imageWidth = drawable.intrinsicSize.width.toInt()
                    imageHeight = drawable.intrinsicSize.height.toInt()
                }
            )
        }

        // 渐变遮罩 - 仅在需要时显示
        if (showGradients) {
            // 顶部渐变遮罩 - 固定位置
            val colors = listOf(Color(0xFF000000), Color(0x00000000))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(120.dp)
                    .background(
                        brush = Brush.verticalGradient(colors),
                    )
            )

            // 底部渐变遮罩 - 固定位置
            val bottomColors = listOf(
                Color(0x001C1523),
                Color(0xFF1C1523)
            )
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(300.dp)
                    .background(
                        brush = Brush.verticalGradient(bottomColors),
                    )
                    .align(Alignment.BottomCenter)
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
fun ChatBackgroundPreview() {
    val mockAgent = AgentInfo(
        id = "test",
        name = "Test Agent",
        avatar = "",
        background = "",
        intro = "Test introduction"
    )
    ChatBackground(agentInfo = mockAgent)
}

@Preview(showBackground = true)
@Composable
fun AgentBackgroundPreview() {
    val mockAgent = AgentInfo(
        id = "test",
        name = "Test Agent", 
        avatar = "",
        background = "",
        intro = "Test introduction"
    )
    AgentBackground(
        agentInfo = mockAgent,
        showGradients = true
    )
}

/**
 * 展示不同宽高比比较的示例
 */
@Composable
fun AspectRatioComparisonExample() {
    // 示例：不同屏幕和图片宽高比的组合
    val examples = listOf(
        "屏幕 9:16 (0.56) + 图片 9:16 (0.56) → Fit (完整显示)",
        "屏幕 16:9 (1.78) + 图片 9:16 (0.56) → FillWidth (填充宽度)",
        "屏幕 9:16 (0.56) + 图片 16:9 (1.78) → FillHeight (填充高度)",
        "屏幕 1:1 (1.0) + 图片 4:3 (1.33) → FillHeight (填充高度)",
        "屏幕 4:3 (1.33) + 图片 1:1 (1.0) → FillWidth (填充宽度)"
    )

    // 这里可以添加实际的 UI 展示
    // 为了简化，这里只是概念展示
}
