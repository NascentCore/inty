package ai.sxwl.android.design.ui

import ai.sxwl.android.design.R
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay

/**
 * Snackbar颜色数据类
 */
private data class SnackbarColors(
    val backgroundColor: Color,
    val textColor: Color,
    val iconColor: Color,
    val icon: Painter
)

/**
 * 自定义Snackbar类型
 */
enum class HeartSnackbarType {
    SUCCESS,    // 成功
    ERROR,      // 错误
    WARNING,    // 警告
    INFO        // 信息
}

/**
 * 自定义Snackbar数据类
 */
data class HeartSnackbarData(
    val message: String,
    val type: HeartSnackbarType = HeartSnackbarType.INFO,
    val duration: Long = 3000L, // 默认3秒
    val actionLabel: String? = null,
    val onAction: (() -> Unit)? = null
)

/**
 * 自定义Snackbar组件
 * 符合IntelliMate应用的设计风格
 */
@Composable
fun HeartSnackbar(
    data: HeartSnackbarData,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    var visible by remember { mutableStateOf(true) }
// 隐藏自动
    LaunchedEffect(data) {
        delay(data.duration)
        visible = false
    }

    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically(
            animationSpec = tween(300),
            initialOffsetY = { it }
        ) + fadeIn(animationSpec = tween(300)),
        exit = slideOutVertically(
            animationSpec = tween(300),
            targetOffsetY = { it }
        ) + fadeOut(animationSpec = tween(300)),
        modifier = modifier
    ) {
        HeartSnackbarContent(
            data = data,
            onDismiss = {
                visible = false
                onDismiss()
            }
        )
    }
}

/**
 * Snackbar内容组件
 */
@Composable
private fun HeartSnackbarContent(
    data: HeartSnackbarData,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val snackbarColors = when (data.type) {
        HeartSnackbarType.SUCCESS -> {
            val bg = Color(0xFF1A472A) // 深绿色背景
            val text = Color(0xFF4CAF50) // 绿色文字
            val icon = Color(0xFF4CAF50) // 绿色图标
            val iconPainter = painterResource(R.drawable.icon_checked_circle)
            SnackbarColors(bg, text, icon, iconPainter)
        }

        HeartSnackbarType.ERROR -> {
            val bg = Color(0xFF3D1F1F) // 深红色背景
            val text = Color(0xFFF44336) // 红色文字
            val icon = Color(0xFFF44336) // 红色图标
            val iconPainter = painterResource(R.drawable.icon_error)
            SnackbarColors(bg, text, icon, iconPainter)
        }

        HeartSnackbarType.WARNING -> {
            val bg = Color(0xFF3D2F1F) // 深橙色背景
            val text = Color(0xFFFF9800) // 橙色文字
            val icon = Color(0xFFFF9800) // 橙色图标
            val iconPainter = painterResource(R.drawable.icon_warn)
            SnackbarColors(bg, text, icon, iconPainter)
        }

        HeartSnackbarType.INFO -> {
            val bg = Color(0xFF1F2A3D) // 深蓝色背景
            val text = Color(0xFF2196F3) // 蓝色文字
            val icon = Color(0xFF2196F3) // 蓝色图标
            val iconPainter = painterResource(R.drawable.icon_info)
            SnackbarColors(bg, text, icon, iconPainter)
        }
    }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(snackbarColors.backgroundColor)
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
// 图标
            Icon(
                painter = snackbarColors.icon,
                contentDescription = null,
                tint = snackbarColors.iconColor,
                modifier = Modifier.size(24.dp)
            )
// 消息文本
            Text(
                text = data.message,
                color = snackbarColors.textColor,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Start
            )
// 操作按钮（如果有）
            data.actionLabel?.let { label ->
                Text(
                    text = label,
                    color = snackbarColors.textColor,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(start = 8.dp)
                )
            }
        }
    }
}

/**
 * 自定义SnackbarHost
 */
@Composable
fun HeartSnackbarHost(
    hostState: SnackbarHostState,
    modifier: Modifier = Modifier,
    snackbar: @Composable (data: HeartSnackbarData, onDismiss: () -> Unit) -> Unit = { data, onDismiss ->
        HeartSnackbar(data = data, onDismiss = onDismiss)
    }
) {
    SnackbarHost(
        hostState = hostState,
        modifier = modifier,
        snackbar = { snackbarData ->
// 将Material3的SnackbarData转换为自定义的HeartSnackbarData
            val heartData = HeartSnackbarData(
                message = snackbarData.visuals.message,
                type = HeartSnackbarType.INFO, // 默认类型
                actionLabel = snackbarData.visuals.actionLabel,
                onAction = { snackbarData.performAction() }
            )

            snackbar(heartData) {
// 这里可以添加自定义的关闭逻辑
            }
        }
    )
}

/**
 * 扩展函数：显示成功Snackbar
 */
suspend fun SnackbarHostState.showSuccessSnackbar(
    message: String,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
): SnackbarResult {
    return showSnackbar(
        message = message,
        actionLabel = actionLabel,
        duration = SnackbarDuration.Short
    )
}

/**
 * 扩展函数：显示错误Snackbar
 */
suspend fun SnackbarHostState.showErrorSnackbar(
    message: String,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
): SnackbarResult {
    return showSnackbar(
        message = message,
        actionLabel = actionLabel,
        duration = SnackbarDuration.Long
    )
}

/**
 * 扩展函数：显示警告Snackbar
 */
suspend fun SnackbarHostState.showWarningSnackbar(
    message: String,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
): SnackbarResult {
    return showSnackbar(
        message = message,
        actionLabel = actionLabel,
        duration = SnackbarDuration.Short
    )
}

/**
 * 扩展函数：显示信息Snackbar
 */
suspend fun SnackbarHostState.showInfoSnackbar(
    message: String,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null
): SnackbarResult {
    return showSnackbar(
        message = message,
        actionLabel = actionLabel,
        duration = SnackbarDuration.Short
    )
}
//区域Preview

@Preview(showBackground = true)
@Composable
private fun HeartSnackbarSuccessPreview() {
    HeartSnackbar(
        data = HeartSnackbarData(
            message = "登录成功",
            type = HeartSnackbarType.SUCCESS
        ),
        onDismiss = {}
    )
}

@Preview(showBackground = true)
@Composable
private fun HeartSnackbarErrorPreview() {
    HeartSnackbar(
        data = HeartSnackbarData(
            message = "登录失败，请重试",
            type = HeartSnackbarType.ERROR
        ),
        onDismiss = {}
    )
}

@Preview(showBackground = true)
@Composable
private fun HeartSnackbarWarningPreview() {
    HeartSnackbar(
        data = HeartSnackbarData(
            message = "网络连接不可用，请检查网络设置",
            type = HeartSnackbarType.WARNING
        ),
        onDismiss = {}
    )
}

@Preview(showBackground = true)
@Composable
private fun HeartSnackbarInfoPreview() {
    HeartSnackbar(
        data = HeartSnackbarData(
            message = "正在加载用户信息...",
            type = HeartSnackbarType.INFO
        ),
        onDismiss = {}
    )
}

@Preview(showBackground = true)
@Composable
private fun HeartSnackbarWithActionPreview() {
    HeartSnackbar(
        data = HeartSnackbarData(
            message = "消息发送失败",
            type = HeartSnackbarType.ERROR,
            actionLabel = "重试",
            onAction = {}
        ),
        onDismiss = {}
    )
}
//区域结束
