package com.ai.intellimate.demo

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.InputContainerConfig
import ai.sxwl.android.design.ui.InputFieldConfig
import ai.sxwl.android.design.ui.MultiPanelInputField
import ai.sxwl.android.design.ui.PanelButtonConfig
import ai.sxwl.android.design.ui.PanelConfig
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import com.ai.intellimate.R

@Composable
fun MultiPanelInputFieldDemoScreen(navController: NavController) {
    var inputText by remember { mutableStateOf("") }
    val messages = remember { mutableStateListOf<String>() }
    val focusRequester = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current
    var currentPanelId by remember { mutableStateOf<String?>(null) }

    // 先获取字符串资源（在 composable 上下文中）
    val replyStyleText = stringResource(R.string.reply_style)
    val resetText = stringResource(R.string.str_reset)
    val feedbackText = stringResource(R.string.str_feedback)
    val reportText = stringResource(R.string.str_report)

    // 创建更多面板配置
    val morePanelConfig = remember(replyStyleText, resetText, feedbackText, reportText) {
        object : PanelConfig {
            override val id = "more"
            override val name = "更多面板"

            @Composable
            override fun PanelContent(
                modifier: Modifier,
                onDismiss: () -> Unit,
                onItemSelected: (Any) -> Unit,
            ) {
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp),
                    maxItemsInEachRow = 4,
                ) {
                    // 回复风格
                    MorePanelItem(
                        icon = R.drawable.icon_reply_chat,
                        text = replyStyleText,
                        isVip = true,
                        onClick = {
                            messages.add("点击了回复风格")
                            ToastUtils.showShort(R.string.reply_style)
                        },
                    )
                    // 重置
                    MorePanelItem(
                        icon = R.drawable.icon_reset_chat,
                        text = resetText,
                        onClick = {
                            messages.add("点击了重置")
                            ToastUtils.showShort(R.string.str_reset)
                        },
                    )
                    // 反馈
                    MorePanelItem(
                        icon = R.drawable.icon_feedback,
                        text = feedbackText,
                        onClick = {
                            messages.add("点击了反馈")
                            ToastUtils.showShort(R.string.str_feedback)
                        },
                    )
                    // 举报
                    MorePanelItem(
                        icon = R.drawable.icon_report,
                        text = reportText,
                        onClick = {
                            messages.add("点击了举报")
                            ToastUtils.showShort(R.string.str_report)
                        },
                    )
                    // Call
                    MorePanelItem(
                        icon = R.drawable.icon_call,
                        text = "Call",
                        onClick = {
                            messages.add("点击了Call")
                            ToastUtils.showShort("Call")
                        },
                    )
                }
            }
        }
    }

    // 创建面板按钮配置
    val panelButtons = remember(morePanelConfig, currentPanelId) {
        listOf(
            // 发送按钮（无输入时显示加号，有输入时显示发送）
            PanelButtonConfig(
                panelConfig = null,
                icon = {
                    AsyncImage(
                        modifier = Modifier.size(32.dp),
                        model = R.drawable.btn_send,
                        contentDescription = null,
                    )
                },
                isVisible = true,
            ),
            // 更多面板按钮
            PanelButtonConfig(
                panelConfig = morePanelConfig,
                icon = {
                    AsyncImage(
                        modifier = Modifier.size(32.dp),
                        model = if (currentPanelId == "more") R.drawable.btn_down else R.drawable.btn_add2,
                        contentDescription = null,
                    )
                },
                isVisible = true,
            ),
        )
    }

    Column(modifier = Modifier
        .fillMaxSize()
        .background(HeartColor.primaryColor)) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp)
                .background(AppColors.DarkPurpleOverlay60)
                .navigationBarsPadding(),
            contentAlignment = Alignment.CenterStart,
        ) {
            Image(
                modifier = Modifier
                    .size(48.dp)
                    .padding(start = 16.dp)
                    .noRippleClickable { navController.popBackStack() },
                painter = painterResource(R.drawable.back),
                contentDescription = "返回",
            )
            Text(
                text = "MultiPanelInputField 演示",
                modifier = Modifier.align(Alignment.Center),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
            )
        }

        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .clickable {
                    focusManager.clearFocus()
                    currentPanelId = null
                }
        ) {
            if (messages.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "发送一些消息来测试输入框功能",
                        color = Color.White.copy(alpha = 0.5f),
                        fontSize = 14.sp,
                    )
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 8.dp),
                ) {
                    items(messages) { message ->
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(
                                    color = Color.White.copy(alpha = 0.1f),
                                    shape = RoundedCornerShape(12.dp)
                                )
                                .padding(12.dp),
                        ) {
                            Text(
                                text = message,
                                color = Color.White,
                                fontSize = 16.sp,
                            )
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        MultiPanelInputField(
            value = inputText,
            onValueChange = { inputText = it },
            panelButtons = panelButtons,
            onSendMessage = {
                if (inputText.isNotBlank()) {
                    messages.add(inputText)
                    inputText = ""
                    ToastUtils.showShort("发送消息")
                }
            },
            onPanelItemSelected = { panelId, item ->
                // 面板项选择已在 PanelContent 中处理
            },
            inputFieldConfig = InputFieldConfig(
                placeholder = "输入消息...",
                maxLength = 200,
            ),
            inputContainerConfig = InputContainerConfig(
                backgroundColor = AppColors.DarkPurpleOverlay60,
                cornerRadius = 12.dp,
                horizontalPadding = 16.dp,
                topPadding = 12.dp,
                bottomPadding = 12.dp,
                minHeight = 56.dp,
                maxHeight = 120.dp,
            ),
            focusRequester = focusRequester,
            onFocusChange = { isFocused ->
                if (isFocused) {
                    currentPanelId = null
                }
            },
            onPanelVisibilityChange = { panelId ->
                currentPanelId = panelId
            },
            externalPanelId = currentPanelId,
        )
    }
}

@Composable
private fun MorePanelItem(
    icon: Int,
    text: String,
    isVip: Boolean = false,
    onClick: () -> Unit,
) {
    Column(
        modifier = Modifier
            .noRippleClickable { onClick() },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(64.dp)
                .background(
                    color = Color.White.copy(0.05f),
                    shape = RoundedCornerShape(8.dp)
                )
        ) {
            Image(
                modifier = Modifier
                    .size(36.dp)
                    .align(Alignment.Center),
                painter = painterResource(id = icon),
                contentDescription = null,
            )
            if (isVip) {
                Image(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(top = 5.dp, end = 2.dp),
                    painter = painterResource(R.drawable.ic_vip_badge),
                    contentDescription = null,
                )
            }
        }
        Spacer(Modifier.height(6.dp))
        Text(text = text, fontSize = 14.sp, color = Color.White)
    }
}
