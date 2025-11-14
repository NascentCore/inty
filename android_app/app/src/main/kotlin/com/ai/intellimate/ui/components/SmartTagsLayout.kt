package com.ai.intellimate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** 智能 Tags 布局组件，支持自动换行和截断 确保不会显示被截断的 tag */
@Composable
fun SmartTagsLayout(
    tags: List<String>,
    modifier: Modifier = Modifier,
    maxLines: Int = 1,
    isCardTag: Boolean = false,
    horizontalArrangement: Arrangement.Horizontal =
        Arrangement.spacedBy(if (isCardTag) 3.dp else 6.dp),
) {
    val density = LocalDensity.current

    // 使用 BoxWithConstraints 在布局阶段就获取可用宽度，避免闪动
    // 这是最简单高效的方案，不需要估算或等待 onGloballyPositioned
    BoxWithConstraints(modifier = modifier.fillMaxWidth()) {
        // 在布局阶段就获取到实际可用宽度（px）
        val availableWidthPx = with(density) { constraints.maxWidth.toFloat() }

        // 计算可见的 tags，使用实际宽度
        val visibleTags = remember(tags, availableWidthPx, maxLines, density) {
            if (availableWidthPx > 0) {
                calculateVisibleTags(
                    tags = tags,
                    availableWidth = availableWidthPx,
                    density = density,
                    maxLines = maxLines,
                )
            } else {
                emptyList()
            }
        }

        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = horizontalArrangement,
            maxItemsInEachRow = Int.MAX_VALUE,
        ) {
            visibleTags.forEach { tag ->
                if (isCardTag) {
                    LiteTagItem(tag)
                } else {
                    TagItem(text = tag)
                }
            }
        }
    }
}

/** 计算可以完全显示的 tags */
private fun calculateVisibleTags(
    tags: List<String>,
    availableWidth: Float,
    density: Density,
    maxLines: Int,
): List<String> {
    if (tags.isEmpty()) return emptyList()

    val tagSpacing = with(density) { 6.dp.toPx() }
    val visibleTags = mutableListOf<String>()
    var currentLineWidth = 0f
    var currentLine = 1

    for (tag in tags) {
        val estimatedTagWidth = estimateTagWidth(tag, density)

        if (
            currentLineWidth + estimatedTagWidth + tagSpacing > availableWidth &&
                currentLine < maxLines
        ) {
            currentLine++
            currentLineWidth = estimatedTagWidth
        } else if (
            currentLineWidth + estimatedTagWidth + tagSpacing > availableWidth &&
                currentLine >= maxLines
        ) {
            break
        } else {
            currentLineWidth += estimatedTagWidth + tagSpacing
        }

        visibleTags.add(tag)
    }

    return visibleTags
}

/** 估算 tag 的宽度 */
private fun estimateTagWidth(text: String, density: Density): Float {
    val charWidth = with(density) { 7.dp.toPx() }
    val horizontalPadding = with(density) { 12.dp.toPx() }
    return text.length * charWidth + horizontalPadding
}

@Composable
private fun TagItem(text: String) {
    Box(
        modifier =
            Modifier
                .background(color = Color(0xff1C1523), shape = RoundedCornerShape(4.dp))
                .border(
                    width = 1.dp,
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(
                                    Color.Transparent,
                                    Color.White.copy(0.09f),
                                    Color.Transparent,
                                )
                        ),
                    shape = RoundedCornerShape(4.dp),
                )
    ) {
        Text(
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 5.dp),
            text = text,
            fontSize = 12.sp,
            fontWeight = FontWeight.Light,
            color = Color.White.copy(0.55f),
        )
    }
}

@Composable
private fun LiteTagItem(text: String) {
    Box(
        modifier =
            Modifier
                .background(color = Color(0xff1C1523), shape = RoundedCornerShape(4.dp))
                .border(
                    width = .5.dp,
                    brush =
                        Brush.horizontalGradient(
                            colors = listOf(Color(0xFF842BA7), Color(0xFF331141))
                        ),
                    shape = RoundedCornerShape(4.dp),
                )
    ) {
        Text(
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp),
            text = text,
            fontSize = 10.sp,
            lineHeight = 12.sp,
            fontWeight = FontWeight.Normal,
            color = Color(0x8CFFFFFF),
        )
    }
}
