package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.utils.UnifiedStartupManager
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 启动状态枚举
 */
enum class InitState {
    Loading,
    Success,
    Failed
}

/**
 * 简化的启动ViewModel
 * 只负责UI状态管理，所有启动逻辑由UnifiedStartupManager处理
 */
class SplashViewModel : BaseActivityViewModel() {

    private val _initState = MutableStateFlow(InitState.Loading)
    val initState = _initState.asStateFlow()

    /**
     * 启动初始化流程
     */
    fun initTask() {
        EasyLog.log("SplashViewModel - 开始启动流程")

        viewModelScope.launch(Dispatchers.IO) {
            try {
                // 等待统一启动管理器完成启动
                waitForStartupCompletion()
                
                // 启动完成，跳转到主页面
                _initState.value = InitState.Success
                EasyLog.log("SplashViewModel - 启动流程完成")
                
            } catch (e: Exception) {
                EasyLog.log("SplashViewModel - 启动失败: ${e.message}", EasyLog.ERROR)
                _initState.value = InitState.Failed
            }
        }
    }

    /**
     * 等待启动完成
     */
    private suspend fun waitForStartupCompletion() {
        // 等待启动管理器完成所有阶段
        while (!UnifiedStartupManager.isStartupCompleted()) {
            kotlinx.coroutines.delay(100) // 100ms检查一次
        }
        
        EasyLog.log("SplashViewModel - 启动管理器完成，状态: ${UnifiedStartupManager.startupState.value}")
    }
}
