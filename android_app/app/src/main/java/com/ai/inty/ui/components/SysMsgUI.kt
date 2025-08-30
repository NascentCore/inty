package com.ai.inty.ui.components

import android.content.Context
import android.content.Intent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.net.toUri
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.SysMsgItem
import com.inty.utils.convertUtcToLocal

/**
 * 系统消息容器组件
 */
@Composable
fun SysMsgItemContainer(
    msg: SysMsgItem,
    showClick: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val context = LocalContext.current
    Column(
        modifier = Modifier
            .padding(16.dp, 16.dp, 16.dp, 9.dp)
            .noRippleClickable {
                msg.linkUrls.firstOrNull()?.let { onClickUrl(context, it) }
            },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        // 时间标签
        Box(
            modifier = Modifier
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(12.dp))
                .padding(8.dp, 1.dp)
        ) {
            Text(
                text = convertUtcToLocal(msg.createdAt),
                fontSize = 12.sp,
                color = Color.White.copy(0.55f)
            )
        }
        Spacer(Modifier.height(10.dp))

        // 消息内容容器
        Column(
            modifier = Modifier
                .background(
                    color = Color(0x3378599A),
                    shape = RoundedCornerShape(8.dp)
                )
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
                ),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            content()

            // 点击提示区域
            if (showClick) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(1.dp)
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(Color.Transparent, Color.White, Color.Transparent)
                            )
                        )
                ) {}

                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        modifier = Modifier.padding(16.dp, 14.dp),
                        text = stringResource(R.string.click_to_check_full),
                        fontSize = 14.sp,
                        color = Color.White.copy(0.55f)
                    )

                    Spacer(Modifier.weight(1f))

                    Image(
                        modifier = Modifier
                            .padding(16.dp, 14.dp)
                            .noRippleClickable {
                                // 点击处理
                            },
                        painter = painterResource(R.drawable.icon_next),
                        contentDescription = null,
                    )
                }
            }
        }
    }
}

/**
 * 图片+文本+链接消息项
 */
@Composable
fun SysMsgItemImageTextLink(msg: SysMsgItem) {
    SysMsgItemContainer(
        msg = msg,
        showClick = true,
    ) {
        IntyImage(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp, 8.dp, 0.dp, 0.dp)),
            model = msg.imageUrls.firstOrNull()
        )
        Text(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            text = msg.content,
            fontSize = 14.sp,
            color = Color.White
        )
    }
}

/**
 * 纯图片消息项
 */
@Composable
fun SysMsgItemImage(msg: SysMsgItem) {
    SysMsgItemContainer(
        msg = msg,
        showClick = false,
    ) {
        IntyImage(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp)),
            model = msg.imageUrls.firstOrNull()
        )
    }
}

/**
 * 图片+链接消息项
 */
@Composable
fun SysMsgItemImageLink(msg: SysMsgItem) {
    SysMsgItemContainer(
        msg = msg,
        showClick = true,
    ) {
        IntyImage(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp, 8.dp, 0.dp, 0.dp)),
            model = msg.imageUrls.firstOrNull()
        )
    }
}

/**
 * 文本+链接消息项
 */
@Composable
fun SysMsgItemTextLink(
    msg: SysMsgItem,
    showClick: Boolean = true,
) {
    SysMsgItemContainer(
        msg = msg,
        showClick = showClick,
    ) {
        Text(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            text = msg.content,
            fontSize = 14.sp,
            color = Color.White
        )
    }
}

/**
 * 处理URL点击事件
 */
fun onClickUrl(context: Context, url: String) {
    val intent = Intent(Intent.ACTION_VIEW, url.toUri())
    context.startActivity(intent)
}

// Preview 函数
@Preview(showBackground = true)
@Composable
fun SysMsgItemContainerPreview() {
    val mockMsg = SysMsgItem(
        id = "1",
        content = "这是一条测试消息内容",
        templateId = 1,
        createdAt = "2024-01-01T10:00:00Z",
        imageUrls = listOf(),
        linkUrls = listOf("https://example.com")
    )

    SysMsgItemContainer(
        msg = mockMsg,
        showClick = true
    ) {
        Text(
            text = "预览内容",
            color = Color.White,
            fontSize = 14.sp
        )
    }
}

@Preview(showBackground = true)
@Composable
fun SysMsgItemTextLinkPreview() {
    val mockMsg = SysMsgItem(
        id = "1",
        content = "这是一条文本消息，包含链接",
        templateId = 1,
        createdAt = "2024-01-01T10:00:00Z",
        imageUrls = listOf(),
        linkUrls = listOf("https://example.com")
    )

    SysMsgItemTextLink(mockMsg)
}

@Preview(showBackground = true)
@Composable
fun SysMsgItemImagePreview() {
    val mockMsg = SysMsgItem(
        id = "1",
        content = "",
        templateId = 4,
        createdAt = "2024-01-01T10:00:00Z",
        imageUrls = listOf("https://example.com/image.jpg"),
        linkUrls = listOf()
    )

    SysMsgItemImage(mockMsg)
}

@Preview(showBackground = true)
@Composable
fun SysMsgItemImageLinkPreview() {
    val mockMsg = SysMsgItem(
        id = "1",
        content = "",
        templateId = 2,
        createdAt = "2024-01-01T10:00:00Z",
        imageUrls = listOf("https://example.com/image.jpg"),
        linkUrls = listOf("https://example.com")
    )

    SysMsgItemImageLink(mockMsg)
}

@Preview(showBackground = true)
@Composable
fun SysMsgItemImageTextLinkPreview() {
    val mockMsg = SysMsgItem(
        id = "1",
        content = "这是一条包含图片和文本的消息",
        templateId = 5,
        createdAt = "2024-01-01T10:00:00Z",
        imageUrls = listOf("https://example.com/image.jpg"),
        linkUrls = listOf("https://example.com")
    )

    SysMsgItemImageTextLink(mockMsg)
}
