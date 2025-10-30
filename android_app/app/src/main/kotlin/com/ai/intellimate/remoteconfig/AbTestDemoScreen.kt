package com.ai.intellimate.remoteconfig

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * AB 测试 Demo 界面
 */
@Composable
fun AbTestDemoScreen(
    viewModel: AbTestDemoViewModel
) {
    val uiState by viewModel.uiState.collectAsState()
    
    if (uiState.isLoading) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator()
        }
        return
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 标题
        Text(
            text = "🔥 Firebase Remote Config",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        
        Text(
            text = "AB 测试演示",
            style = MaterialTheme.typography.titleMedium,
            color = Color.Gray
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        // 配置状态
        ConfigStatusCard(uiState)
        
        // 欢迎消息
        WelcomeMessageCard(uiState)
        
        // AB 测试按钮
        AbTestButtonCard(uiState)
        
        // 功能开关
        FeatureToggleCard(uiState)
        
        // 所有配置信息
        AllConfigsCard(uiState)
        
        // 刷新按钮
        Button(
            onClick = { viewModel.refreshConfig() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("🔄 重新获取配置")
        }
        
        // 错误信息
        uiState.error?.let { error ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = Color(0xFFFFEBEE)
                )
            ) {
                Text(
                    text = "❌ 错误: $error",
                    modifier = Modifier.padding(16.dp),
                    color = Color.Red
                )
            }
        }
    }
}

@Composable
private fun ConfigStatusCard(uiState: AbTestUiState) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (uiState.configActivated) Color(0xFFE8F5E9) else Color(0xFFFFF3E0)
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "配置状态",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = if (uiState.configActivated) {
                    "✅ 已成功获取远程配置"
                } else {
                    "⚠️ 使用默认配置"
                }
            )
        }
    }
}

@Composable
private fun WelcomeMessageCard(uiState: AbTestUiState) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "欢迎消息 (welcome_message)",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = uiState.welcomeMessage,
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
private fun AbTestButtonCard(uiState: AbTestUiState) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "按钮 AB 测试",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "button_color: ${uiState.buttonColor}",
                fontSize = 12.sp,
                color = Color.Gray
            )
            Text(
                text = "button_text: ${uiState.buttonText}",
                fontSize = 12.sp,
                color = Color.Gray
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Button(
                onClick = { /* 这里可以添加点击事件 */ },
                colors = ButtonDefaults.buttonColors(
                    containerColor = parseColor(uiState.buttonColor)
                ),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(uiState.buttonText)
            }
        }
    }
}

@Composable
private fun FeatureToggleCard(uiState: AbTestUiState) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "功能开关 (feature_enabled)",
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = if (uiState.featureEnabled) "功能已启用" else "功能已禁用",
                    fontSize = 14.sp,
                    color = Color.Gray
                )
            }
            Switch(
                checked = uiState.featureEnabled,
                onCheckedChange = null,
                enabled = false
            )
        }
    }
}

@Composable
private fun AllConfigsCard(uiState: AbTestUiState) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "所有配置参数",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            
            if (uiState.allConfigs.isEmpty()) {
                Text("暂无配置", color = Color.Gray)
            } else {
                uiState.allConfigs.forEach { (key, value) ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                    ) {
                        Text(
                            text = "$key: ",
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                        Text(
                            text = value,
                            fontSize = 12.sp,
                            color = Color.Gray
                        )
                    }
                }
            }
        }
    }
}

/**
 * 解析颜色字符串
 */
private fun parseColor(colorString: String): Color {
    return try {
        Color(android.graphics.Color.parseColor(colorString))
    } catch (e: Exception) {
        Color(0xFF6200EE) // 默认颜色
    }
}
