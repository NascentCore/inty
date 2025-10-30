package com.ai.intellimate.abtest

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * AB 测试 ViewModel
 * 管理 AB 测试相关的 UI 状态
 */
class ABTestViewModel : ViewModel() {
    
    private val abTestManager: ABTestManager = ABTestModule.getABTestManager()
    
    private val _uiState = MutableStateFlow(ABTestUIState())
    val uiState: StateFlow<ABTestUIState> = _uiState.asStateFlow()
    
    init {
        initializeABTest()
    }
    
    /**
     * 初始化 AB 测试
     */
    private fun initializeABTest() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            try {
                abTestManager.initializeABTest()
                updateUIState()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "AB 测试初始化失败"
                )
            }
        }
    }
    
    /**
     * 更新 UI 状态
     */
    private fun updateUIState() {
        val config = abTestManager.getCurrentConfig()
        
        _uiState.value = _uiState.value.copy(
            isLoading = false,
            buttonColor = config.getWelcomeButtonColor(),
            buttonText = config.getWelcomeButtonText(),
            showPremiumBanner = config.shouldShowPremiumBanner(),
            chatUIStyle = config.getChatUIStyle(),
            newUIFeatureEnabled = config.isNewUIFeatureEnabled(),
            allConfigs = config.getAllConfigs()
        )
    }
    
    /**
     * 处理按钮点击
     */
    fun onButtonClick(buttonType: String) {
        abTestManager.logButtonClicked(buttonType)
        _uiState.value = _uiState.value.copy(
            lastClickedButton = buttonType
        )
    }
    
    /**
     * 刷新配置
     */
    fun refreshConfig() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            try {
                val success = abTestManager.getCurrentConfig().fetchAndActivate()
                if (success) {
                    updateUIState()
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = "配置刷新失败"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "配置刷新失败"
                )
            }
        }
    }
    
    /**
     * 清除错误状态
     */
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}

/**
 * AB 测试 UI 状态
 */
data class ABTestUIState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val buttonColor: String = "blue",
    val buttonText: String = "开始体验",
    val showPremiumBanner: Boolean = true,
    val chatUIStyle: String = "modern",
    val newUIFeatureEnabled: Boolean = false,
    val lastClickedButton: String? = null,
    val allConfigs: Map<String, Any> = emptyMap()
)