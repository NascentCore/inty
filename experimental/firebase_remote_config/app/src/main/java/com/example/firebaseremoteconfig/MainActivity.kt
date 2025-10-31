package com.example.firebaseremoteconfig

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    
    private val viewModel: MainViewModel by viewModels()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            MaterialTheme {
                ABTestDemoScreen(viewModel = viewModel)
            }
        }
    }
}

class MainViewModel : ViewModel() {
    
    private val remoteConfigManager = RemoteConfigManager.getInstance()
    
    var buttonVariant by mutableStateOf(ABTestVariant.CONTROL)
        private set
    
    var welcomeMessage by mutableStateOf("")
        private set
    
    var isNewFeatureEnabled by mutableStateOf(false)
        private set
    
    var configStatus by mutableStateOf("加载中...")
        private set
    
    var isLoading by mutableStateOf(false)
        private set
    
    init {
        loadConfig()
    }
    
    fun loadConfig() {
        viewModelScope.launch {
            isLoading = true
            try {
                val variantString = remoteConfigManager.getButtonColorVariant()
                buttonVariant = ABTestVariant.fromString(variantString)
                welcomeMessage = remoteConfigManager.getWelcomeMessage()
                isNewFeatureEnabled = remoteConfigManager.isNewFeatureEnabled()
                configStatus = "配置已加载\n${remoteConfigManager.getConfigInfo()}"
            } catch (e: Exception) {
                configStatus = "加载配置失败: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }
    
    fun refreshConfig() {
        viewModelScope.launch {
            isLoading = true
            try {
                val updated = remoteConfigManager.fetchAndActivate()
                if (updated) {
                    loadConfig()
                    configStatus = "配置已更新\n${remoteConfigManager.getConfigInfo()}"
                } else {
                    configStatus = "配置已是最新\n${remoteConfigManager.getConfigInfo()}"
                }
            } catch (e: Exception) {
                configStatus = "刷新配置失败: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }
}

@Composable
fun ABTestDemoScreen(viewModel: MainViewModel) {
    val buttonVariant by viewModel.buttonVariant.collectAsState()
    val welcomeMessage by viewModel.welcomeMessage.collectAsState()
    val isNewFeatureEnabled by viewModel.isNewFeatureEnabled.collectAsState()
    val configStatus by viewModel.configStatus.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 标题
        Text(
            text = "Firebase Remote Config AB 测试演示",
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center
        )
        
        // 欢迎消息
        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "欢迎消息",
                    style = MaterialTheme.typography.titleMedium
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = welcomeMessage,
                    style = MaterialTheme.typography.bodyLarge
                )
            }
        }
        
        // AB 测试按钮展示
        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "当前按钮变体: ${buttonVariant.displayName}",
                    style = MaterialTheme.typography.titleMedium
                )
                Spacer(modifier = Modifier.height(16.dp))
                
                Button(
                    onClick = { },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = buttonVariant.buttonColor
                    ),
                    modifier = Modifier.width(200.dp)
                ) {
                    Text("测试按钮")
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                // 显示所有可能的变体（仅用于演示）
                Text(
                    text = "可能的值: control, variant_a, variant_b",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        
        // 新功能开关
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
                Text(
                    text = "新功能",
                    style = MaterialTheme.typography.titleMedium
                )
                Switch(
                    checked = isNewFeatureEnabled,
                    onCheckedChange = { }
                )
            }
        }
        
        // 配置状态
        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "配置状态",
                    style = MaterialTheme.typography.titleMedium
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = configStatus,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        
        // 刷新按钮
        Button(
            onClick = { viewModel.refreshConfig() },
            enabled = !isLoading,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = MaterialTheme.colorScheme.onPrimary
                )
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text("刷新配置")
        }
        
        // 说明文字
        Text(
            text = "在 Firebase Console 中配置 Remote Config 参数来改变应用行为",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp)
        )
    }
}
