package com.ai.intellimate.demo

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.InputContainerConfig
import ai.sxwl.android.design.ui.InputFieldConfig
import ai.sxwl.android.design.ui.MultiPanelInputField
import ai.sxwl.android.design.ui.PanelButtonConfig
import ai.sxwl.android.design.ui.PanelConfig
import ai.sxwl.android.design.ui.PanelContainerConfig
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.ai.intellimate.R
import kotlinx.coroutines.launch

/**
 * MultiPanelInputField 演示页面
 * 
 * 展示 MultiPanelInputField 组件的各种功能和使用方式
 */
@Composable
fun MultiPanelInputFieldDemoScreen(navController: NavController) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val focusManager = LocalFocusManager.current
    var inputText by remember { mutableStateOf("") }
    val messages = remember { mutableStateListOf<String>() }
    val focusRequester = remember { FocusRequester() }
    var currentPanelId by remember { mutableStateOf<String?>(null) }
    
    // 表情包面板配置（使用匿名对象）
    val emojiPanelConfig = remember {
        object : PanelConfig {
            override val id = "emoji"
            override val name = "表情包面板"
            
            private val emojis = listOf(
                "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
                "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
                "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩",
                "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "😣", "😖",
            )
            
            @Composable
            override fun PanelContent(
                modifier: Modifier,
                onDismiss: () -> Unit,
                onItemSelected: (Any) -> Unit,
            ) {
                FlowRow(
                    modifier = modifier,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    emojis.forEach { emoji ->
                        Box(
                            modifier = Modifier
                                .size(48.dp)
                                .background(
                                    color = Color.White.copy(alpha = 0.1f),
                                    shape = RoundedCornerShape(8.dp)
                                )
                                .noRippleClickable {
                                    onItemSelected(emoji)
                                },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                text = emoji,
                                fontSize = 24.sp,
                            )
                        }
                    }
                }
            }
        }
    }
    
    // 礼物背包面板配置（使用匿名对象）
    val giftPanelConfig = remember {
        object : PanelConfig {
            override val id = "gift"
            override val name = "礼物背包面板"
            
            private val gifts = listOf(
                "🎁", "💝", "🌹", "💐", "🎀", "🎊", "🎉", "✨", "⭐", "💫",
                "🌟", "💖", "💗", "💓", "💞", "💕", "💟", "❣️", "💔", "❤️",
            )
            
            @Composable
            override fun PanelContent(
                modifier: Modifier,
                onDismiss: () -> Unit,
                onItemSelected: (Any) -> Unit,
            ) {
                FlowRow(
                    modifier = modifier,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    gifts.forEach { gift ->
                        Box(
                            modifier = Modifier
                                .size(64.dp)
                                .background(
                                    color = Color.White.copy(alpha = 0.1f),
                                    shape = RoundedCornerShape(12.dp)
                                )
                                .noRippleClickable {
                                    onItemSelected(gift)
                                },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                text = gift,
                                fontSize = 32.sp,
                            )
                        }
                    }
                }
            }
        }
    }
    
    // 定义面板按钮配置
    val panelButtons = remember(emojiPanelConfig, giftPanelConfig) {
        listOf(
            // 表情包面板按钮
            PanelButtonConfig(
                panelConfig = emojiPanelConfig,
                icon = {
                    Text("😊", fontSize = 20.sp)
                },
            ),
            // 礼物面板按钮
            PanelButtonConfig(
                panelConfig = giftPanelConfig,
                icon = {
                    Text("🎁", fontSize = 20.sp)
                },
            ),
            // 发送按钮（panelConfig 为 null）
            PanelButtonConfig(
                panelConfig = null,
                icon = {
                    Text("➤", fontSize = 20.sp, color = Color.White)
                },
            ),
        )
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(HeartColor.primaryColor)
    ) {
        // 顶部栏
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            contentAlignment = Alignment.CenterStart,
        ) {
            Image(
                modifier = Modifier
                    .size(24.dp)
                    .align(Alignment.CenterStart)
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
        
        // 消息列表区域（可滚动）
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            if (messages.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp)
                        .clickable {
                            // 点击空白区域，清除焦点并关闭面板
                            focusManager.clearFocus()
                            currentPanelId = null
                        },
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
                                .padding(12.dp)
                                .clickable {
                                    // 点击消息项，清除焦点并关闭面板
                                    focusManager.clearFocus()
                                    currentPanelId = null
                                },
                        ) {
                            Text(
                                text = message,
                                color = Color.White,
                                fontSize = 14.sp,
                            )
                        }
                    }
                }
            }
        }
        
        Spacer(modifier = Modifier.height(8.dp))
        
        // 输入框区域
        MultiPanelInputField(
            value = inputText,
            onValueChange = { inputText = it },
            panelButtons = panelButtons,
            onSendMessage = {
                if (inputText.isNotBlank()) {
                    messages.add(inputText)
                    inputText = ""
                    scope.launch {
                        ToastUtils.showShort("消息已发送")
                    }
                }
            },
            onPanelItemSelected = { panelId, item ->
                when (panelId) {
                    "emoji" -> {
                        // 插入表情到输入框
                        inputText += item.toString()
                    }
                    "gift" -> {
                        // 处理礼物选择，添加到消息中
                        val giftMessage = "发送了礼物: $item"
                        messages.add(giftMessage)
                        scope.launch {
                            ToastUtils.showShort("礼物已发送: $item")
                        }
                    }
                }
            },
            inputFieldConfig = InputFieldConfig(
                placeholder = "输入消息...",
                maxLines = 4,
                maxLength = 500,
            ),
            inputContainerConfig = InputContainerConfig(
                backgroundColor = Color(0x9937303D),
                cornerRadius = 12.dp,
            ),
            panelContainerConfig = PanelContainerConfig(
                backgroundColor = HeartColor.primaryColor,
                animationDuration = 300,
            ),
            focusRequester = focusRequester,
            onPanelVisibilityChange = { panelId ->
                currentPanelId = panelId
            },
            externalPanelId = currentPanelId,
            bottomPadding = 0.dp,
        )
    }
}
