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
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.inty.base.IntyImage
import com.ai.inty.beans.AgentInfo
import com.ai.inty.utils.getChatBackground
import kotlin.math.roundToInt

/**
 * 聊天背景组件
 */
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
 * 通用角色背景组件
 * 可用于聊天页面、角色主页等需要角色背景的地方
 */
@Composable
fun AgentBackground(
    agentInfo: AgentInfo?,
    modifier: Modifier = Modifier,
    showGradients: Boolean = true,
) {
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current

    var imageWidthDp by remember {
        mutableIntStateOf(configuration.screenWidthDp)
    }
    var imageHeightDp by remember {
        mutableIntStateOf(configuration.screenHeightDp)
    }

    if (configuration.screenWidthDp > imageWidthDp) {
        imageWidthDp = configuration.screenWidthDp
    }
    if (configuration.screenHeightDp > imageHeightDp) {
        imageHeightDp = configuration.screenHeightDp
    }

    Box(modifier = modifier) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState(), false)
                .onSizeChanged {
                    val newHeight = with(density) {
                        it.height.toDp().value.roundToInt()
                    }
                    if (newHeight > imageHeightDp) {
                        imageHeightDp = newHeight
                    }
                }
        ) {
            IntyImage(
                modifier = Modifier
                    .size(imageWidthDp.dp, imageHeightDp.dp),
                model = agentInfo?.getChatBackground(),
                alignment = Alignment.TopCenter,
                contentScale = ContentScale.Crop,
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
