package com.ai.inty.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.SysMsgItem
import com.ai.inty.ui.components.SysMsgItemImage
import com.ai.inty.ui.components.SysMsgItemImageLink
import com.ai.inty.ui.components.SysMsgItemImageTextLink
import com.ai.inty.ui.components.SysMsgItemTextLink

/**
 * 系统消息模板ID枚举
 */
enum class SysMsgTemplateId(val id: Int) {
    TEXT_WITH_LINK(1),
    IMAGE_WITH_LINK(2),
    TEXT_ONLY(3),
    IMAGE_ONLY(4),
    IMAGE_TEXT_LINK(5),
}

/**
 * 系统消息屏幕
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SysMsgsScreen(
    msgs: List<SysMsgItem>,
    onBack: () -> Unit = {},
) {
    Box(
        modifier = Modifier.fillMaxSize()
    ) {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            topBar = {
                CenterAlignedTopAppBar(
                    title = {
                        Text(
                            text = stringResource(R.string.sys_notify_title),
                            color = Color.White,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 20.sp,
                        )
                    },
                    navigationIcon = {
                        Image(
                            modifier = Modifier
                                .padding(horizontal = 12.dp)
                                .noRippleClickable {
                                    onBack()
                                },
                            painter = painterResource(R.drawable.back),
                            contentDescription = null,
                        )
                    }
                )
            }
        ) { innerPadding ->
            LazyColumn(
                modifier = Modifier.padding(innerPadding)
            ) {
                runCatching {
                    if (msgs.isNotEmpty()) {
                        itemsIndexed(
                            items = msgs,
                            key = { index, msg -> "${msg.id}_$index" }
                        ) { index, msg ->
                            when (msg.templateId) {
                                SysMsgTemplateId.TEXT_WITH_LINK.id -> {
                                    SysMsgItemTextLink(msg)
                                }

                                SysMsgTemplateId.IMAGE_WITH_LINK.id -> {
                                    SysMsgItemImageLink(msg)
                                }

                                SysMsgTemplateId.TEXT_ONLY.id -> {
                                    SysMsgItemTextLink(msg, false)
                                }

                                SysMsgTemplateId.IMAGE_ONLY.id -> {
                                    SysMsgItemImage(msg)
                                }

                                SysMsgTemplateId.IMAGE_TEXT_LINK.id -> {
                                    SysMsgItemImageTextLink(msg)
                                }
                            }
                        }
                    }
                }.onFailure { it.printStackTrace() }

            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun SysMsgsScreenPreview() {
    val mockMsgs = listOf(
        SysMsgItem(
            id = "1",
            content = "这是一条文本消息，包含链接",
            templateId = 1,
            createdAt = "2024-01-01T10:00:00Z",
            imageUrls = listOf(),
            linkUrls = listOf("https://example.com")
        ),
        SysMsgItem(
            id = "2",
            content = "",
            templateId = 4,
            createdAt = "2024-01-01T11:00:00Z",
            imageUrls = listOf("https://example.com/image.jpg"),
            linkUrls = listOf()
        ),
        SysMsgItem(
            id = "3",
            content = "这是一条包含图片和文本的消息",
            templateId = 5,
            createdAt = "2024-01-01T12:00:00Z",
            imageUrls = listOf("https://example.com/image.jpg"),
            linkUrls = listOf("https://example.com")
        )
    )

    SysMsgsScreen(
        msgs = mockMsgs,
        onBack = {}
    )
}
