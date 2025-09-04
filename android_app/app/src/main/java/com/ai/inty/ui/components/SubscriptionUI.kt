package com.ai.inty.ui.components

import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.net.toUri
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.inty.utils.log.EasyLog

/**
 * 订阅管理项组件
 */
@Composable
fun SubscriptionManagementItem(
    icon: Int,
    title: String,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .padding(horizontal = 12.dp)
            .noRippleClickable { onClick() },
        verticalAlignment = Alignment.CenterVertically
    ) {
        // 图标
        Box(
            modifier = Modifier
                .size(32.dp)
                .background(
                    color = when (icon) {
                        R.drawable.icon_list_row_1 -> Color(0xFF2196F3) // 蓝色
                        R.drawable.icon_list_row_2 -> Color(0xFFE91E63) // 粉色
                        R.drawable.icon_list_row_3 -> Color(0xFFFF9800) // 橙色
                        else -> Color(0xFF9C27B0) // 默认紫色
                    },
                    shape = RoundedCornerShape(6.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(icon),
                contentDescription = null,
                modifier = Modifier.size(20.dp)
            )
        }

        Spacer(Modifier.width(12.dp))

        // 标题
        Text(
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White
        )

        Spacer(Modifier.weight(1f))

        // 右箭头
        Image(
            painter = painterResource(R.drawable.icon_next),
            contentDescription = null,
        )
    }
}

/**
 * 订阅管理容器组件
 */
@Composable
fun SubscriptionManagementContainer(
    content: @Composable () -> Unit
) {
    Column(
        modifier = Modifier
            .padding(horizontal = 16.dp)
            .fillMaxWidth()
            .border(
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.White.copy(0.2f),
                        Color.Transparent
                    )
                ),
                width = 1.dp,
                shape = RoundedCornerShape(8.dp)
            )
            .background(
                color = Color(0x3378599A),
                shape = RoundedCornerShape(8.dp)
            )
    ) {
        Spacer(Modifier.height(8.dp))
        content()
        Spacer(Modifier.height(8.dp))
    }
}


/**
 * 实际执行跳转逻辑的辅助函数，放置在Composable外部。
 * 它需要 Context 参数来启动 Intent。
 */
fun openPlayStoreSubscriptions(context: Context) {
    try {
        val uri = "https://play.google.com/store/account/subscriptions".toUri()
        val intent = Intent(Intent.ACTION_VIEW, uri)

        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
            EasyLog.log("✅ 成功跳转到 Google Play 订阅管理页面")
        } else {
            EasyLog.log("❌ 没有找到可以处理 Google Play 订阅管理页面的应用")
            Toast.makeText(
                context,
                context.getString(R.string.toast_google_play_unavailable),
                Toast.LENGTH_LONG
            ).show()
        }
    } catch (e: Exception) {
        EasyLog.log("❌ 跳转到 Google Play 订阅管理页面失败: ${e.message}")
        Toast.makeText(
            context,
            context.getString(R.string.toast_navigation_failed),
            Toast.LENGTH_LONG
        ).show()
    }
}

// Preview 函数
@Preview(showBackground = true)
@Composable
fun SubscriptionManagementItemPreview() {
    SubscriptionManagementItem(
        icon = R.drawable.icon_list_row_1,
        title = "恢复订阅",
        onClick = {}
    )
}

@Preview(showBackground = true)
@Composable
fun SubscriptionManagementContainerPreview() {
    SubscriptionManagementContainer {
        SubscriptionManagementItem(
            icon = R.drawable.icon_list_row_1,
            title = "恢复订阅",
            onClick = {}
        )
    }
}
