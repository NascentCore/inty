package com.ai.intellimate.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.DrawerValue
import androidx.compose.runtime.Composable
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import kotlin.math.absoluteValue

@Composable
fun MyModalNavigationDrawer(
    drawerContent: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    drawerState: MutableState<DrawerValue> = remember { mutableStateOf(DrawerValue.Closed) },
    content: @Composable () -> Unit,
) {
    val configuration = LocalConfiguration.current
    val screenWidthDp = configuration.screenWidthDp
    val screenWidthPx = with(LocalDensity.current) { screenWidthDp.dp.toPx() }

    Box(modifier.fillMaxSize()) {
        // 是否显示遮罩层
        val showMask = remember { mutableStateOf(false) }
        // 抽屉宽度
        val drawerWidth = remember { mutableIntStateOf(0) }
        // 抽屉的 x 位置
        val xOffset by
            animateFloatAsState(
                targetValue =
                    if (drawerState.value == DrawerValue.Closed) screenWidthPx.toFloat()
                    else screenWidthPx - drawerWidth.value.toFloat(),
                animationSpec = tween(durationMillis = 400),
            )
        // 半透明
        val maskLayerAlpha by
            animateFloatAsState(
                targetValue = if (drawerState.value == DrawerValue.Closed) 0f else 0.6f,
                animationSpec = tween(durationMillis = 400),
                finishedListener = { showMask.value = it.absoluteValue > 0f },
            )
        // 内容
        Box { content() }
        // 遮罩
        if (showMask.value || drawerState.value == DrawerValue.Open) {
            Box(
                modifier =
                    Modifier.fillMaxSize()
                        .alpha(maskLayerAlpha)
                        .background(color = Color(0xff000000))
                        .clickable { drawerState.value = DrawerValue.Closed }
            ) {}
            // 抽屉
            Box(
                modifier =
                    Modifier.onSizeChanged { drawerWidth.intValue = it.width }
                        .graphicsLayer { translationX = xOffset }
            ) {
                drawerContent()
            }
        }
    }
}
