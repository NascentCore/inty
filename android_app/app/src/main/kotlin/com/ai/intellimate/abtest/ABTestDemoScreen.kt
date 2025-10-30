package com.ai.intellimate.abtest

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

/**
 * AB 测试演示界面
 * 展示 Firebase Remote Config 的 AB 测试功能
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ABTestDemoScreen(
    viewModel: ABTestViewModel = remember { ABTestViewModel() }
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    
    LaunchedEffect(Unit) {
        viewModel.refreshConfig()
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AB 测试演示") },
                actions = {
                    IconButton(onClick = { viewModel.refreshConfig() }) {
                        Text("刷新")
                    }
                }
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 加载状态
            if (uiState.isLoading) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth(),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator()
                    }
                }
            }
            
            // 错误状态
            uiState.error?.let { error ->
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp)
                        ) {
                            Text(
                                text = "错误",
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onErrorContainer
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = error,
                                color = MaterialTheme.colorScheme.onErrorContainer
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Button(
                                onClick = { viewModel.clearError() }
                            ) {
                                Text("确定")
                            }
                        }
                    }
                }
            }
            
            // 欢迎横幅
            item {
                WelcomeBanner(
                    buttonColor = uiState.buttonColor,
                    buttonText = uiState.buttonText,
                    showPremiumBanner = uiState.showPremiumBanner,
                    onButtonClick = { viewModel.onButtonClick("welcome") }
                )
            }
            
            // UI 样式展示
            item {
                UIStyleCard(
                    chatUIStyle = uiState.chatUIStyle,
                    newUIFeatureEnabled = uiState.newUIFeatureEnabled,
                    onStyleChange = { viewModel.onButtonClick("ui_style") }
                )
            }
            
            // 配置信息展示
            item {
                ConfigInfoCard(
                    configs = uiState.allConfigs,
                    lastClickedButton = uiState.lastClickedButton
                )
            }
        }
    }
}

@Composable
private fun WelcomeBanner(
    buttonColor: String,
    buttonText: String,
    showPremiumBanner: Boolean,
    onButtonClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = when (buttonColor) {
                "red" -> Color(0xFFFFEBEE)
                "green" -> Color(0xFFE8F5E8)
                "purple" -> Color(0xFFF3E5F5)
                else -> Color(0xFFE3F2FD)
            }
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "欢迎使用 Inty",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "体验 AI 陪伴的乐趣",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Button(
                onClick = onButtonClick,
                colors = ButtonDefaults.buttonColors(
                    containerColor = when (buttonColor) {
                        "red" -> Color(0xFFD32F2F)
                        "green" -> Color(0xFF388E3C)
                        "purple" -> Color(0xFF7B1FA2)
                        else -> Color(0xFF1976D2)
                    }
                ),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text(buttonText)
            }
            
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
                        fontWeight = FontWeight.Medium,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}

@Composable
private fun UIStyleCard(
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
                text = "界面样式",
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
                    text = "聊天界面样式: $chatUIStyle",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Button(
                    onClick = onStyleChange,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (newUIFeatureEnabled) 
                            MaterialTheme.colorScheme.primary 
                        else 
                            MaterialTheme.colorScheme.secondary
                    )
                ) {
                    Text("切换样式")
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "新 UI 功能: ",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = if (newUIFeatureEnabled) 
                            Color(0xFF4CAF50) 
                        else 
                            Color(0xFF9E9E9E)
                    )
                ) {
                    Text(
                        text = if (newUIFeatureEnabled) "已启用" else "未启用",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        color = Color.White,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}

@Composable
private fun ConfigInfoCard(
    configs: Map<String, Any>,
    lastClickedButton: String?
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "配置信息",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            if (lastClickedButton != null) {
                Text(
                    text = "最后点击: $lastClickedButton",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.height(8.dp))
            }
            
            configs.forEach { (key, value) ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = key,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                    Text(
                        text = value.toString(),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
            }
        }
    }
}