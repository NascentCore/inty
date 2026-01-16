package com.ai.intellimate.ui.components

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import kotlinx.coroutines.delay
import kotlin.time.Duration.Companion.milliseconds

/**
 * 轮播背景组件
 *
 * 用于在登录页面等场景中展示多张背景图片的轮播效果，支持透明度渐变过渡。
 *
 * @param imageResIds 背景图片资源ID列表，至少需要一张图片
 * @param modifier Modifier
 * @param transitionDuration 过渡动画时长（毫秒），默认为 2000ms
 * @param displayDuration 每张图片显示时长（毫秒），默认为 5000ms
 */
@Composable
fun CarouselBackground(
    imageResIds: List<Int>,
    modifier: Modifier = Modifier,
    onPageChange: (Int) -> Unit = {},
    transitionDuration: Int = 1000,
    displayDuration: Int = 3000
) {
    Box(modifier = modifier) {
        val pageChangeCall by rememberUpdatedState(onPageChange)

        if (imageResIds.isNotEmpty()) {
            var imageRes by remember { mutableIntStateOf(imageResIds[0]) }

            LaunchedEffect(imageResIds) {
                generateSequence(0) { it + 1}
                    .forEach {
                        val index = it % imageResIds.size
                        imageRes = imageResIds[index]

                        pageChangeCall(index)
                        delay(displayDuration.milliseconds)
                    }
            }

            AnimatedContent(
                targetState = imageRes,
                transitionSpec = {
                    fadeIn(tween(transitionDuration))
                        .togetherWith(fadeOut(tween(transitionDuration, transitionDuration)))
                },
                modifier = Modifier.fillMaxSize()
            ) {
                Image(
                    painter = painterResource(it),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
            }
        }

        Spacer(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.verticalGradient(
                        0.4f to Color(0x00300C4F),
                        .75f to Color(0xFF300C4F)
                    )
                )
        )
    }
}
