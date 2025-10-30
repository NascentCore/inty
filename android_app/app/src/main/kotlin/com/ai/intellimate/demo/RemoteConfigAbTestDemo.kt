package com.ai.intellimate.demo

import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Firebase Remote Config AB 测试演示
 *
 * 演示如何使用 Remote Config 进行 AB 测试：
 * 1. 从 Remote Config 获取实验组配置（按钮颜色）
 * 2. 根据配置显示不同的 UI
 * 3. 记录用户行为到 Analytics
 *
 * 使用说明：
 * 1. 在 Firebase Console 中配置 Remote Config：
 *    - 参数名: `button_color_variant`
 *    - 类型: String
 *    - 默认值: "blue" (可选值: "blue", "red", "green")
 *    - 可以通过条件（Conditions）基于用户属性进行 AB 测试
 *
 * 2. 设置 AB 测试条件（可选）：
 *    - 例如：50% 用户显示蓝色按钮，50% 用户显示红色按钮
 *    - 可以通过用户属性、应用版本、设备类型等条件进行分组
 */
@Composable
fun RemoteConfigAbTestDemo(
    modifier: Modifier = Modifier
) {
    var buttonColor by remember { mutableStateOf("blue") }
    var isLoading by remember { mutableStateOf(true) }
    var clickCount by remember { mutableStateOf(0) }

    // 获取 Remote Config 配置
    LaunchedEffect(Unit) {
        try {
            // 从服务器获取最新配置
            FirebaseManager.fetchRemoteConfig()

            // 读取配置值
            val variant = FirebaseManager.getRemoteConfigString(
                key = "button_color_variant",
                defaultValue = "blue"
            )
            buttonColor = variant

            LogUtils.d("RemoteConfigAbTest", "获取到按钮颜色变体: $variant")

            // 记录用户分组到 Analytics（用于 AB 测试分析）
            FirebaseManager.logEvent(
                eventName = "ab_test_assigned",
                parameters = mapOf(
                    "experiment_name" to "button_color_test",
                    "variant" to variant
                )
            )
        } catch (e: Exception) {
            LogUtils.e("RemoteConfigAbTest", "获取 Remote Config 失败: ${e.message}")
        } finally {
            isLoading = false
        }
    }

    Box(
        modifier = modifier
            .background(Color.White)
            .padding(16.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            Text(
                text = "Firebase Remote Config\nAB 测试演示",
                fontSize = 24.sp,
                color = Color.Black
            )

            if (isLoading) {
                Text(
                    text = "加载配置中...",
                    fontSize = 16.sp,
                    color = Color.Gray
                )
            } else {
                // 根据配置显示不同颜色的按钮
                val backgroundColor = when (buttonColor) {
                    "red" -> Color.Red
                    "green" -> Color.Green
                    else -> Color.Blue // 默认蓝色
                }

                Button(
                    onClick = {
                        clickCount++
                        // 记录用户交互事件
                        FirebaseManager.logEvent(
                            eventName = "ab_test_button_clicked",
                            parameters = mapOf(
                                "experiment_name" to "button_color_test",
                                "variant" to buttonColor,
                                "click_count" to clickCount
                            )
                        )
                        LogUtils.d(
                            "RemoteConfigAbTest",
                            "按钮被点击: variant=$buttonColor, count=$clickCount"
                        )
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = backgroundColor
                    ),
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) {
                    Text(
                        text = "点击我 (变体: $buttonColor)",
                        color = Color.White
                    )
                }

                Text(
                    text = "当前实验组: $buttonColor\n点击次数: $clickCount",
                    fontSize = 14.sp,
                    color = Color.Gray
                )

                Text(
                    text = "说明：\n" +
                        "• 按钮颜色由 Remote Config 控制\n" +
                        "• 可在 Firebase Console 修改配置\n" +
                        "• 支持基于用户属性的 AB 测试",
                    fontSize = 12.sp,
                    color = Color.Gray
                )
            }
        }
    }
}