package com.ai.intellimate.abtest

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/**
 * AB 测试集成示例
 * 展示如何在现有界面中集成 AB 测试功能
 */
@Composable
fun ABTestIntegrationExample() {
    val abTestConfig = remember { ABTestModule.getABTestConfig() }
    val abTestManager = remember { ABTestModule.getABTestManager() }
    
    // 获取 AB 测试配置
    val buttonColor = abTestConfig.getWelcomeButtonColor()
    val buttonText = abTestConfig.getWelcomeButtonText()
    val showPremiumBanner = abTestConfig.shouldShowPremiumBanner()
    val chatUIStyle = abTestConfig.getChatUIStyle()
    val newUIFeatureEnabled = abTestConfig.isNewUIFeatureEnabled()
    
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 根据 AB 测试配置显示不同的欢迎界面
        WelcomeSection(
            buttonColor = buttonColor,
            buttonText = buttonText,
            showPremiumBanner = showPremiumBanner,
            onButtonClick = { abTestManager.logButtonClicked("welcome") }
        )
        
        // 根据 AB 测试配置显示不同的聊天界面样式
        ChatUISection(
            chatUIStyle = chatUIStyle,
            newUIFeatureEnabled = newUIFeatureEnabled,
            onStyleChange = { abTestManager.logUIStyleChanged() }
        )
        
        // 功能开关示例
        FeatureToggleSection(
            newUIFeatureEnabled = newUIFeatureEnabled
        )
    }
}

@Composable
private fun WelcomeSection(
    buttonColor: String,
    buttonText: String,
    showPremiumBanner: Boolean,
    onButtonClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "欢迎使用 Inty",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "体验 AI 陪伴的乐趣",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // 根据 AB 测试配置显示不同颜色的按钮
            Button(
                onClick = onButtonClick,
                colors = ButtonDefaults.buttonColors(
                    containerColor = when (buttonColor) {
                        "red" -> Color(0xFFD32F2F)
                        "green" -> Color(0xFF388E3C)
                        "purple" -> Color(0xFF7B1FA2)
                        else -> Color(0xFF1976D2)
                    }
                )
            ) {
                Text(buttonText)
            }
            
            // 根据 AB 测试配置决定是否显示高级功能横幅
            if (showPremiumBanner) {
                Spacer(modifier = Modifier.height(12.dp))
                
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xFFFFD700)
                    )
                ) {
                    Text(
                        text = "✨ 升级到高级版解锁更多功能",
                        modifier = Modifier.padding(12.dp),
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}

@Composable
private fun ChatUISection(
    chatUIStyle: String,
    newUIFeatureEnabled: Boolean,
    onStyleChange: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "聊天界面",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "当前样式: $chatUIStyle",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Button(onClick = onStyleChange) {
                    Text("切换样式")
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            // 根据新 UI 功能开关显示不同内容
            if (newUIFeatureEnabled) {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xFFE8F5E8)
                    )
                ) {
                    Text(
                        text = "🆕 新 UI 功能已启用",
                        modifier = Modifier.padding(12.dp),
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color(0xFF2E7D32)
                    )
                }
            } else {
                Text(
                    text = "使用经典界面",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun FeatureToggleSection(
    newUIFeatureEnabled: Boolean
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "功能开关",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "新 UI 功能",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Switch(
                    checked = newUIFeatureEnabled,
                    onCheckedChange = { /* 由 Remote Config 控制 */ }
                )
            }
            
            Spacer(modifier = Modifier.height(4.dp))
            
            Text(
                text = if (newUIFeatureEnabled) "功能已启用" else "功能已禁用",
                style = MaterialTheme.typography.bodySmall,
                color = if (newUIFeatureEnabled) 
                    Color(0xFF2E7D32) 
                else 
                    MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}