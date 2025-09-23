package com.ai.inty.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * 智能 Tags 布局组件，支持自动换行和截断
 * 确保不会显示被截断的 tag
 */
@Composable
fun SmartTagsLayout(
    tags: List<String>,
    modifier: Modifier = Modifier,
    maxLines: Int = 1,
    horizontalArrangement: Arrangement.Horizontal = Arrangement.spacedBy(6.dp),
    isCardTag: Boolean = false,//标记是否是在explore现实的tag，目前主要用于AgentInfo和Explore的card
) {
    val density = LocalDensity.current
    var availableWidth by remember { mutableFloatStateOf(0f) }
    var visibleTags by remember { mutableStateOf(tags) }

    // 计算可见的 tags
    LaunchedEffect(tags, availableWidth) {
        if (availableWidth > 0) {
            visibleTags = calculateVisibleTags(
                tags = tags,
                availableWidth = availableWidth,
                density = density,
                maxLines = maxLines
            )
        }
    }

    FlowRow(
        modifier = modifier
            .fillMaxWidth()
            .onGloballyPositioned { layoutCoordinates ->
                availableWidth = layoutCoordinates.size.width.toFloat()
            },
        horizontalArrangement = horizontalArrangement,
        maxItemsInEachRow = Int.MAX_VALUE
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


/**
 * 计算可以完全显示的 tags
 */
private fun calculateVisibleTags(
    tags: List<String>,
    availableWidth: Float,
    density: androidx.compose.ui.unit.Density,
    maxLines: Int
): List<String> {
    if (tags.isEmpty()) return emptyList()

    val tagSpacing = with(density) { 6.dp.toPx() }
    val tagHeight = with(density) { 24.dp.toPx() } // 估算 tag 高度
    val maxHeight = tagHeight * maxLines

    val visibleTags = mutableListOf<String>()
    var currentLineWidth = 0f
    var currentLine = 1

    for (tag in tags) {
        // 估算 tag 宽度（文本宽度 + padding）
        val estimatedTagWidth = estimateTagWidth(tag, density)

        // 检查是否需要换行
        if (currentLineWidth + estimatedTagWidth + tagSpacing > availableWidth && currentLine < maxLines) {
            currentLine++
            currentLineWidth = estimatedTagWidth
        } else if (currentLineWidth + estimatedTagWidth + tagSpacing > availableWidth && currentLine >= maxLines) {
            // 当前行已满且已达到最大行数，停止添加
            break
        } else {
            currentLineWidth += estimatedTagWidth + tagSpacing
        }

        visibleTags.add(tag)
    }

    return visibleTags
}


/**
 * 估算 tag 的宽度
 */
private fun estimateTagWidth(text: String, density: androidx.compose.ui.unit.Density): Float {
    // 基于字符数量估算宽度，这是一个简化的估算方法
    val charWidth = with(density) { 7.dp.toPx() } // 每个字符大约 7dp
    val horizontalPadding = with(density) { 12.dp.toPx() } // 左右 padding 各 6dp
    return text.length * charWidth + horizontalPadding
}

@Composable
private fun TagItem(text: String) {
    Box(
        modifier = Modifier
            .background(color = Color(0xff1C1523), shape = RoundedCornerShape(4.dp))
            .border(
                width = 1.dp,
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.White.copy(0.09f),
                        Color.Transparent
                    )
                ),
                shape = RoundedCornerShape(4.dp)
            )
    ) {
        Text(
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 5.dp),
            text = text,
            fontSize = 12.sp,
            fontWeight = FontWeight.Light,
            color = Color.White.copy(0.55f)
        )
    }
}


@Composable
private fun LiteTagItem(text: String) {
    Box(
        modifier = Modifier
            .background(color = Color(0xff1C1523), shape = RoundedCornerShape(4.dp))
            .border(
                width = 1.dp,
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.White.copy(0.09f),
                        Color.Transparent
                    )
                ),
                shape = RoundedCornerShape(4.dp)
            )
    ) {
        Text(
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp),
            text = text,
            fontSize = 12.sp,
            lineHeight = 12.sp,
            fontWeight = FontWeight.Light,
            color = Color.White.copy(0.55f)
        )
    }
}
