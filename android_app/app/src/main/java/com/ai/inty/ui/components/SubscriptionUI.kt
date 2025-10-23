package com.ai.inty.ui.components

import ai.sxwl.android.utils.ToastUtils
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import com.ai.inty.R

/** 订阅管理容器组件 */
@Composable
fun SubscriptionManagementContainer(content: @Composable () -> Unit) {
    Column(
        modifier =
            Modifier
                .padding(horizontal = 16.dp)
                .fillMaxWidth()
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                    width = 1.dp,
                    shape = RoundedCornerShape(8.dp),
                )
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(8.dp))
    ) {
        Spacer(Modifier.height(8.dp))
        content()
        Spacer(Modifier.height(8.dp))
    }
}

/** 实际执行跳转逻辑的辅助函数，放置在Composable外部。 它需要 Context 参数来启动 Intent。 */
fun openPlayStoreSubscriptions(context: Context) {
    try {
        val uri = "https://play.google.com/store/account/subscriptions".toUri()
        val intent = Intent(Intent.ACTION_VIEW, uri)

        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
        } else {
            ToastUtils.showShort(R.string.toast_google_play_unavailable)
        }
    } catch (e: Exception) {
        ToastUtils.showShort(R.string.toast_navigation_failed)
    }
}
