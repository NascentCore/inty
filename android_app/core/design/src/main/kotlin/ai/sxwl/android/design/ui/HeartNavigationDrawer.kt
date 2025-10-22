package ai.sxwl.android.design.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.width
import androidx.compose.material3.DrawerValue
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.PointerInputChange
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import kotlin.math.max
import kotlin.math.min


@Composable
fun HeartModalNavigationDrawer(
    drawerContent: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    drawerState: DrawerValue = DrawerValue.Closed,
    onDrawerStateChange: (DrawerValue) -> Unit = {},
    enableGesture: Boolean = true,
    content: @Composable () -> Unit,
) {
    val screenWidthPx = LocalWindowInfo.current.containerSize.width.toFloat()

    Box(modifier.fillMaxSize()) {
        // 状态管理 - 使用by语法优化
        var showMask by remember { mutableStateOf(false) }
        var drawerWidth by remember { mutableIntStateOf(0) }
        var accumulatedDragOffset by remember { mutableFloatStateOf(0f) }
        var isDragging by remember { mutableStateOf(false) }
        var dragStartState by remember { mutableStateOf(DrawerValue.Closed) }

        // 计算位置
        val targetOffset = if (drawerState == DrawerValue.Closed) {
            screenWidthPx
        } else {
            screenWidthPx - drawerWidth
        }
        val currentOffset = if (isDragging) targetOffset + accumulatedDragOffset else targetOffset

        // 动画
        val xOffset by animateFloatAsState(
            targetValue = currentOffset,
            animationSpec = tween(durationMillis = if (isDragging) 0 else 400)
        )

        val maskLayerAlpha by animateFloatAsState(
            targetValue = if (drawerState == DrawerValue.Closed) 0f else 0.6f,
            animationSpec = tween(durationMillis = if (isDragging) 0 else 400),
            finishedListener = {
                if (it == 0f) {
                    showMask = false
                }
            }
        )

        // 内容区域
        Box {
            content()

            // 边缘拖拽支持
            if (drawerState == DrawerValue.Closed && enableGesture) {
                EdgeDragArea(
                    onDragStart = {
                        isDragging = true
                        dragStartState = DrawerValue.Closed
                        accumulatedDragOffset = 0f
                    },
                    onDragEnd = {
                        isDragging = false
                        val threshold = drawerWidth * 0.5f
                        if (accumulatedDragOffset < -threshold) {
                            onDrawerStateChange(DrawerValue.Open)
                        }
                        accumulatedDragOffset = 0f
                    },
                    onDrag = { _, dragAmount ->
                        accumulatedDragOffset = max(
                            accumulatedDragOffset + dragAmount.x,
                            -drawerWidth.toFloat()
                        )
                    }
                )
            }
        }

        // 遮罩和抽屉
        val shouldShowDrawer = showMask || drawerState == DrawerValue.Open || isDragging
        if (shouldShowDrawer) {
            // 遮罩层
            MaskLayer(
                isDragging = isDragging,
                dragStartState = dragStartState,
                accumulatedDragOffset = accumulatedDragOffset,
                drawerWidth = drawerWidth,
                maskLayerAlpha = maskLayerAlpha,
                onMaskClick = { onDrawerStateChange(DrawerValue.Closed) }
            )

            // 抽屉
            DrawerContent(
                drawerContent = drawerContent,
                isDragging = isDragging,
                dragStartState = dragStartState,
                accumulatedDragOffset = accumulatedDragOffset,
                screenWidthPx = screenWidthPx,
                drawerWidth = drawerWidth,
                xOffset = xOffset,
                enableGesture = enableGesture,
                drawerState = drawerState,
                onDrawerStateChange = onDrawerStateChange,
                onSizeChanged = { drawerWidth = it.width },
                onDragStart = {
                    isDragging = true
                    dragStartState = drawerState
                    accumulatedDragOffset = 0f
                },
                onDragEnd = {
                    isDragging = false
                    val threshold = drawerWidth * 0.5f
                    when (dragStartState) {
                        DrawerValue.Open -> {
                            if (accumulatedDragOffset > threshold) {
                                onDrawerStateChange(DrawerValue.Closed)
                            }
                        }

                        DrawerValue.Closed -> {
                            if (accumulatedDragOffset < -threshold) {
                                onDrawerStateChange(DrawerValue.Open)
                            }
                        }
                    }
                    accumulatedDragOffset = 0f
                },
                onDrag = { _, dragAmount ->
                    when (dragStartState) {
                        DrawerValue.Open -> {
                            if (dragAmount.x > 0) {
                                accumulatedDragOffset = min(
                                    accumulatedDragOffset + dragAmount.x,
                                    drawerWidth.toFloat()
                                )
                            } else if (dragAmount.x < 0) {
                                accumulatedDragOffset = max(
                                    accumulatedDragOffset + dragAmount.x,
                                    0f
                                )
                            }
                        }

                        DrawerValue.Closed -> {
                            if (dragAmount.x < 0) {
                                accumulatedDragOffset = max(
                                    accumulatedDragOffset + dragAmount.x,
                                    -drawerWidth.toFloat()
                                )
                            } else if (dragAmount.x > 0) {
                                accumulatedDragOffset = min(
                                    accumulatedDragOffset + dragAmount.x,
                                    0f
                                )
                            }
                        }
                    }
                }
            )
        }
    }
}

@Composable
private fun EdgeDragArea(
    onDragStart: () -> Unit,
    onDragEnd: () -> Unit,
    onDrag: (PointerInputChange, Offset) -> Unit,
) {
    Box(
        modifier = Modifier
            .width(20.dp)
            .fillMaxSize()
            .pointerInput(Unit) {
                detectDragGestures(
                    onDragStart = { onDragStart() },
                    onDragEnd = { onDragEnd() },
                    onDrag = { change, dragAmount ->
                        change.consume()
                        onDrag(change, dragAmount)
                    }
                )
            }
    )
}

@Composable
private fun MaskLayer(
    isDragging: Boolean,
    dragStartState: DrawerValue,
    accumulatedDragOffset: Float,
    drawerWidth: Int,
    maskLayerAlpha: Float,
    onMaskClick: () -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .alpha(
                if (isDragging) {
                    val progress = if (dragStartState == DrawerValue.Open) {
                        1f - (accumulatedDragOffset / drawerWidth.toFloat())
                    } else {
                        -accumulatedDragOffset / drawerWidth.toFloat()
                    }
                    (0.6f * progress).coerceIn(0f, 0.6f)
                } else {
                    maskLayerAlpha
                }
            )
            .background(color = Color(0xff000000))
            .clickable { onMaskClick() }
    )
}

@Composable
private fun DrawerContent(
    drawerContent: @Composable () -> Unit,
    isDragging: Boolean,
    dragStartState: DrawerValue,
    accumulatedDragOffset: Float,
    screenWidthPx: Float,
    drawerWidth: Int,
    xOffset: Float,
    enableGesture: Boolean,
    drawerState: DrawerValue,
    onDrawerStateChange: (DrawerValue) -> Unit,
    onSizeChanged: (IntSize) -> Unit,
    onDragStart: () -> Unit,
    onDragEnd: () -> Unit,
    onDrag: (PointerInputChange, Offset) -> Unit,
) {
    Box(
        modifier = Modifier
            .onSizeChanged { onSizeChanged(it) }
            .graphicsLayer {
                translationX = if (isDragging) {
                    when (dragStartState) {
                        DrawerValue.Open -> screenWidthPx - drawerWidth + accumulatedDragOffset
                        DrawerValue.Closed -> screenWidthPx + accumulatedDragOffset
                    }
                } else {
                    xOffset
                }
            }
            .pointerInput(Unit) {
                if (enableGesture) {
                    detectDragGestures(
                        onDragStart = { onDragStart() },
                        onDragEnd = { onDragEnd() },
                        onDrag = { change, dragAmount ->
                            change.consume()
                            onDrag(change, dragAmount)
                        }
                    )
                }
            }
    ) {
        drawerContent()
    }
}
