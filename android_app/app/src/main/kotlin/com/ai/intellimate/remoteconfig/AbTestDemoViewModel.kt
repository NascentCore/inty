package com.ai.intellimate.remoteconfig

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * AB 测试 Demo ViewModel
 */
class AbTestDemoViewModel : ViewModel() {
    
    private val _uiState = MutableStateFlow(AbTestUiState())
    val uiState: StateFlow<AbTestUiState> = _uiState.asStateFlow()
    
    init {
        initializeRemoteConfig()
    }
    
    private fun initializeRemoteConfig() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            try {
                // 初始化 Remote Config
                RemoteConfigManager.initialize(fetchIntervalSeconds = 0)
                
                // 获取并激活配置
                val activated = RemoteConfigManager.fetchAndActivate()
                
                // 读取配置值
                val buttonColor = RemoteConfigManager.getString(RemoteConfigManager.ConfigKeys.BUTTON_COLOR)
                val buttonText = RemoteConfigManager.getString(RemoteConfigManager.ConfigKeys.BUTTON_TEXT)
                val featureEnabled = RemoteConfigManager.getBoolean(RemoteConfigManager.ConfigKeys.FEATURE_ENABLED)
                val welcomeMessage = RemoteConfigManager.getString(RemoteConfigManager.ConfigKeys.WELCOME_MESSAGE)
                
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    buttonColor = buttonColor,
                    buttonText = buttonText,
                    featureEnabled = featureEnabled,
                    welcomeMessage = welcomeMessage,
                    configActivated = activated,
                    allConfigs = RemoteConfigManager.getAllConfigs()
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message
                )
            }
        }
    }
    
    fun refreshConfig() {
        initializeRemoteConfig()
    }
}

data class AbTestUiState(
    val isLoading: Boolean = false,
    val buttonColor: String = "#FF6200EE",
    val buttonText: String = "点击我",
    val featureEnabled: Boolean = false,
    val welcomeMessage: String = "欢迎使用我们的应用！",
    val configActivated: Boolean = false,
    val allConfigs: Map<String, String> = emptyMap(),
    val error: String? = null,
    val clickCount: Int = 0
)
