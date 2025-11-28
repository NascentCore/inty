package com.ai.intellimate.ui.components

// CREATED_BY_AGENT

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CornerBasedShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest

/**
 * 角色卡片基础组件，仅负责展示背景图 + 渐变 + 标题/副标题文本。
 * 交互、标签或附加按钮由调用方通过 [overlayContent] / [footerContent] 扩展。
 */
@Composable
fun CharacterCard(
    modifier: Modifier = Modifier,
    imageUrl: String?,
    title: String,
    subtitle: String,
    titleMaxLines: Int = 1,
    subtitleMaxLines: Int = 2,
    shape: Shape = RoundedCornerShape(8.dp),
    gradientBrush: Brush =
        Brush.verticalGradient(
            colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.6f), Color.Black.copy(alpha = 0.95f))
        ),
    textPadding: PaddingValues = PaddingValues(horizontal = 8.dp, vertical = 12.dp),
    shimmerCornerRadius: Dp = 8.dp,
    placeholderResId: Int? = null,
    overlayContent: @Composable BoxScope.() -> Unit = {},
    footerContent: @Composable ColumnScope.() -> Unit = {},
) {
    val context = LocalContext.current
    val cornerShape = shape
    val gradientShape: Shape =
        when {
            shape is CornerBasedShape -> shape
            else -> RoundedCornerShape(8.dp)
        }

    val hasRemoteImage = !imageUrl.isNullOrBlank()
    var imageLoaded by remember(imageUrl) { mutableStateOf(false) }

    Box(modifier = modifier.clip(cornerShape)) {
        when {
            hasRemoteImage -> {
                AsyncImage(
                    modifier = Modifier.fillMaxSize(),
                    model = ImageRequest.Builder(context).data(imageUrl).build(),
                    contentDescription = null,
                    contentScale = androidx.compose.ui.layout.ContentScale.Crop,
                    alignment = Alignment.TopCenter,
                    onSuccess = {
                        if (!imageLoaded) {
                            imageLoaded = true
                        }
                    },
                    onError = {
                        if (imageLoaded) {
                            imageLoaded = false
                        }
                    },
                )
            }

            placeholderResId != null -> {
                Image(
                    modifier = Modifier.fillMaxSize(),
                    painter = painterResource(placeholderResId),
                    contentDescription = null,
                    contentScale = androidx.compose.ui.layout.ContentScale.Crop,
                    alignment = Alignment.TopCenter,
                )
                if (!imageLoaded) {
                    imageLoaded = true
                }
            }
        }

        if (hasRemoteImage && !imageLoaded) {
            ShimmerPlaceholder(modifier = Modifier.fillMaxSize(), cornerRadius = shimmerCornerRadius)
        }

        Box(
            modifier =
                Modifier.fillMaxSize()
                    .background(
                        brush = gradientBrush,
                        shape = gradientShape,
                    )
        )

        Column(
            modifier = Modifier.align(Alignment.BottomStart).padding(textPadding),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                text = title,
                fontSize = 14.sp,
                lineHeight = 22.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = titleMaxLines,
                overflow = TextOverflow.Ellipsis,
            )

            Text(
                text = subtitle,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                fontWeight = FontWeight.Normal,
                color = Color.White.copy(alpha = 0.7f),
                maxLines = subtitleMaxLines,
                overflow = TextOverflow.Ellipsis,
            )

            footerContent()
        }

        overlayContent()
    }
}
