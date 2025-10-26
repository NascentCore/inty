package com.ai.intellimate.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.intellimate.R

/** 空状态类型枚举 */
enum class EmptyStateType {
    /** 数据为空 */
    EMPTY_DATA,

    /** 网络错误 */
    NETWORK_ERROR,

    /** 加载失败 */
    LOAD_ERROR,
}

/** 统一的空状态组件支持不同的空状态类型，包含重试按钮 */
@Composable
fun EmptyStateComponent(
    type: EmptyStateType,
    title: String? = null,
    subtitle: String? = null,
    showRetryButton: Boolean = false,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
// 空状态图标
        AsyncImage(
            model = R.drawable.img_content_empty,
            contentScale = ContentScale.Crop,
            contentDescription = null
        )

        Spacer(Modifier.height(16.dp))
// 标题
        if (title != null) {
            Text(
                text = title,
                color = Color.White.copy(.8f),
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
// 副标题
        if (subtitle != null) {
            Spacer(Modifier.height(8.dp))
            Text(
                text = subtitle,
                color = Color.White.copy(0.6f),
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
// 重试按钮
        if (showRetryButton && onRetry != null) {
            Spacer(Modifier.height(24.dp))
            GradientButton(
                text = stringResource(R.string.retry_button),
                onSave = onRetry,
                modifier = Modifier.padding(horizontal = 32.dp),
            )
        }
    }
}

/** 数据为空状态组件 */
@Composable
fun EmptyDataState(
    title: String? = null,
    subtitle: String? = null,
    showRetryButton: Boolean = false,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    EmptyStateComponent(
        type = EmptyStateType.EMPTY_DATA,
        title = title,
        subtitle = subtitle,
        showRetryButton = showRetryButton,
        onRetry = onRetry,
        modifier = modifier,
    )
}

/** 网络错误状态组件 */
@Composable
fun NetworkErrorState(
    title: String = stringResource(R.string.empty_explore_error),
    subtitle: String? = null,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    EmptyStateComponent(
        type = EmptyStateType.NETWORK_ERROR,
        title = title,
        subtitle = subtitle,
        showRetryButton = false,
        onRetry = onRetry,
        modifier = modifier,
    )
}

/** 加载失败状态组件 */
@Composable
fun LoadErrorState(
    title: String,
    subtitle: String? = null,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    EmptyStateComponent(
        type = EmptyStateType.LOAD_ERROR,
        title = title,
        subtitle = subtitle,
        showRetryButton = false,
        onRetry = onRetry,
        modifier = modifier,
    )
}
// Preview 函数
@Preview(showBackground = true)
@Composable
private fun EmptyDataStatePreview() {
    EmptyDataState(
        title = "No conversations yet",
        subtitle = "Start chatting with your favorite characters!",
    )
}

@Preview(showBackground = true)
@Composable
private fun NetworkErrorStatePreview() {
    NetworkErrorState(
        title = "Failed to load characters",
        subtitle = "Check your connection and try again",
        onRetry = {},
    )
}

@Preview(showBackground = true)
@Composable
private fun LoadErrorStatePreview() {
    LoadErrorState(title = "Loading failed", subtitle = "Something went wrong", onRetry = {})
}
