package com.ai.inty.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.inty.api.client.IntyClient
import com.inty.api.client.IntyClientAsync
import com.inty.api.models.api.v1.auth.AuthCreateGuestResponse
import com.inty.api.models.api.v1.auth.AuthCreateGuestParams
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Inty Kotlin SDK 使用示例 ViewModel
 * 展示如何在 Android 应用中使用 Kotlin SDK
 */
class IntySdkExampleViewModel : ViewModel() {
    
    // 创建 SDK 客户端实例
    private val intyClient: IntyClient by lazy {
        com.inty.api.client.okhttp.IntyOkHttpClient.builder()
            .apiKey("your-api-key") // 这里应该使用实际的 API Key
            .baseUrl("https://app.inty.cc/api/v1")
            .build()
    }
    
    private val intyClientAsync: IntyClientAsync by lazy {
        com.inty.api.client.okhttp.IntyOkHttpClientAsync.builder()
            .apiKey("your-api-key") // 这里应该使用实际的 API Key
            .baseUrl("https://app.inty.cc/api/v1")
            .build()
    }
    
    // UI 状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()
    
    private val _guestUser = MutableStateFlow<AuthCreateGuestResponse?>(null)
    val guestUser: StateFlow<AuthCreateGuestResponse?> = _guestUser.asStateFlow()
    
    /**
     * 示例1：创建访客用户（同步调用）
     * 注意：同步调用应该在后台线程中执行
     */
    fun createGuestUserSync() {
        viewModelScope.launch {
            try {
                _isLoading.value = true
                _errorMessage.value = null
                
                // 在协程中执行同步调用
                val response = kotlinx.coroutines.withContext(Dispatchers.IO) {
                    intyClient.api().v1().auth().createGuest()
                }
                
                _guestUser.value = response
                EasyLog.log("Guest user created successfully")
                
            } catch (e: Exception) {
                EasyLog.log("Failed to create guest user: ${e.message}", EasyLog.ERROR)
                _errorMessage.value = e.message
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    /**
     * 示例2：创建访客用户（异步调用）
     * 推荐使用异步调用，更符合 Kotlin 协程的最佳实践
     */
    fun createGuestUserAsync() {
        viewModelScope.launch {
            try {
                _isLoading.value = true
                _errorMessage.value = null
                
                // 直接使用异步客户端
                val response = intyClientAsync.api().v1().auth().createGuest()
                
                _guestUser.value = response
                EasyLog.log("Guest user created successfully")
                
            } catch (e: Exception) {
                EasyLog.log("Failed to create guest user: ${e.message}", EasyLog.ERROR)
                _errorMessage.value = e.message
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    /**
     * 示例3：带参数的 API 调用
     * 展示如何传递参数给 API
     */
    fun createGuestUserWithParams() {
        viewModelScope.launch {
            try {
                _isLoading.value = true
                _errorMessage.value = null
                
                // 创建带参数的请求
                val params = AuthCreateGuestParams.builder()
                    .build()
                
                val response = intyClientAsync.api().v1().auth().createGuest(params)
                
                _guestUser.value = response
                EasyLog.log("Guest user created with params")
                
            } catch (e: Exception) {
                EasyLog.log("Failed to create guest user with params: ${e.message}", EasyLog.ERROR)
                _errorMessage.value = e.message
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    /**
     * 示例4：错误处理
     * 展示如何处理不同类型的异常
     */
    fun demonstrateErrorHandling() {
        viewModelScope.launch {
            try {
                _isLoading.value = true
                _errorMessage.value = null
                
                // 故意使用无效的 API Key 来触发错误
                val clientWithInvalidKey = com.inty.api.client.okhttp.IntyOkHttpClient.builder()
                    .apiKey("invalid-key")
                    .baseUrl("https://app.inty.cc/api/v1")
                    .build()
                
                val response = clientWithInvalidKey.api().v1().auth().createGuest()
                _guestUser.value = response
                
            } catch (e: com.inty.api.errors.UnauthorizedException) {
                EasyLog.log("Unauthorized: ${e.message}", EasyLog.ERROR)
                _errorMessage.value = "认证失败：${e.message}"
            } catch (e: com.inty.api.errors.BadRequestException) {
                EasyLog.log("Bad Request: ${e.message}", EasyLog.ERROR)
                _errorMessage.value = "请求错误：${e.message}"
            } catch (e: com.inty.api.errors.IntyServiceException) {
                EasyLog.log("Service Error: ${e.message}", EasyLog.ERROR)
                _errorMessage.value = "服务错误：${e.message}"
            } catch (e: Exception) {
                EasyLog.log("Unexpected error: ${e.message}", EasyLog.ERROR)
                _errorMessage.value = "未知错误：${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    /**
     * 清除错误消息
     */
    fun clearError() {
        _errorMessage.value = null
    }
    
    /**
     * 重置状态
     */
    fun reset() {
        _isLoading.value = false
        _errorMessage.value = null
        _guestUser.value = null
    }
}
