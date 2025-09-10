package com.ai.inty.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ai.inty.viewmodels.IntySdkExampleViewModel
import com.inty.api.models.api.v1.auth.AuthCreateGuestResponse

/**
 * Inty Kotlin SDK 使用示例界面
 * 展示如何在 Compose UI 中使用 Kotlin SDK
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IntySdkExampleScreen() {
    // 创建 ViewModel 实例
    val viewModel = remember { IntySdkExampleViewModel() }
    
    // 收集状态
    val isLoading by viewModel.isLoading.collectAsStateWithLifecycle()
    val errorMessage by viewModel.errorMessage.collectAsStateWithLifecycle()
    val guestUser by viewModel.guestUser.collectAsStateWithLifecycle()
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Inty SDK 示例") }
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
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Inty Kotlin SDK 集成示例",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "这个界面展示了如何在 Android 应用中使用 Inty Kotlin SDK",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }
            
            item {
                Text(
                    text = "API 调用示例",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }
            
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = { viewModel.createGuestUserAsync() },
                        enabled = !isLoading,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("创建访客用户 (异步)")
                    }
                    
                    Button(
                        onClick = { viewModel.createGuestUserSync() },
                        enabled = !isLoading,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("创建访客用户 (同步)")
                    }
                }
            }
            
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = { viewModel.createGuestUserWithParams() },
                        enabled = !isLoading,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("带参数调用")
                    }
                    
                    Button(
                        onClick = { viewModel.demonstrateErrorHandling() },
                        enabled = !isLoading,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("错误处理示例")
                    }
                }
            }
            
            // 加载状态
            if (isLoading) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp)
                            )
                            Spacer(modifier = Modifier.width(16.dp))
                            Text("正在调用 API...")
                        }
                    }
                }
            }
            
            // 错误消息
            errorMessage?.let { error ->
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer
                        )
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = error,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onErrorContainer
                            )
                            TextButton(
                                onClick = { viewModel.clearError() }
                            ) {
                                Text("清除")
                            }
                        }
                    }
                }
            }
            
            // 成功结果
            guestUser?.let { user ->
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp)
                        ) {
                            Text(
                                text = "API 调用成功！",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            
                            Text(
                                text = "用户信息：",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Medium
                            )
                            
                            Text(
                                text = "响应数据已接收",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                    }
                }
            }
            
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "使用说明",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        
                        val instructions = listOf(
                            "1. 异步调用：推荐使用，符合 Kotlin 协程最佳实践",
                            "2. 同步调用：在后台线程中执行，避免阻塞 UI",
                            "3. 带参数调用：展示如何传递参数给 API",
                            "4. 错误处理：展示如何处理不同类型的异常",
                            "5. 所有调用都会自动使用当前用户的认证信息"
                        )
                        
                        instructions.forEach { instruction ->
                            Text(
                                text = instruction,
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.padding(vertical = 2.dp)
                            )
                        }
                    }
                }
            }
            
            item {
                Button(
                    onClick = { viewModel.reset() },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("重置状态")
                }
            }
        }
    }
}
