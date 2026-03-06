package com.ai.intellimate.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import kotlin.time.Duration.Companion.milliseconds
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * 轮播背景组件（左右滑动，首尾循环）
 *
 * 用于在登录页面等场景中展示多张背景图片，支持手指左右滑动切换，首尾循环（最后一页左滑进入第一页，第一页右滑进入最后一页），以及定时自动切换到下一页。
 * 切换效果为水平滑动，非渐变。
 *
 * @param imageResIds 背景图片资源ID列表，至少需要一张图片
 * @param modifier Modifier
 * @param onPageChange 当前页索引变化回调，参数为逻辑页索引 [0, imageResIds.size - 1]
 * @param displayDuration 每张图片自动停留时长（毫秒），默认为 3000ms；设为 0 可关闭自动轮播
 */
@Composable
fun CarouselBackground(
    imageResIds: List<Int>,
    modifier: Modifier = Modifier,
    onPageChange: (Int) -> Unit = {},
    displayDuration: Int = 3000,
) {
    Box(modifier = modifier) {
        val pageChangeCall by rememberUpdatedState(onPageChange)

        if (imageResIds.isNotEmpty()) {
            val imageCount = imageResIds.size
            // 大页数 + 从中间开始，实现首尾循环无限滑动
            val totalPages = 1000 * imageCount
            val initialPage = 500 * imageCount
            val pagerState = rememberPagerState(initialPage = initialPage) { totalPages }

            LaunchedEffect(pagerState) {
                snapshotFlow { pagerState.currentPage }
                    .distinctUntilChanged()
                    .collect { pageChangeCall(it % imageCount) }
            }

            if (displayDuration > 0) {
                // 使用稳定 key，避免在 animateScrollToPage 执行过程中因 currentPage 变化导致 effect 重启、滚动被取消只滚一半
                LaunchedEffect(pagerState, displayDuration) {
                    while (true) {
                        delay(displayDuration.milliseconds)
                        val targetPage = pagerState.currentPage + 1
                        pagerState.animateScrollToPage(targetPage)
                    }
                }
            }

            HorizontalPager(
                state = pagerState,
                modifier = Modifier.fillMaxSize(),
                userScrollEnabled = true,
                beyondViewportPageCount = 1,
            ) { page ->
                Image(
                    painter = painterResource(imageResIds[page % imageCount]),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }

        Spacer(
            modifier =
                Modifier.fillMaxSize()
                    .background(
                        brush =
                            Brush.verticalGradient(
                                0.4f to Color(0x00300C4F),
                                .75f to Color(0xFF300C4F),
                            )
                    )
        )
    }
}
