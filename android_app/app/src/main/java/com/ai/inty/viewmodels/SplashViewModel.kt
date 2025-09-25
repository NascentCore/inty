package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import com.ai.inty.utils.UnifiedStartupManager
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** 启动状态枚举 */
enum class InitState {
    Loading,
    Success,
    Failed,
}

/** 简化的启动ViewModel 只负责UI状态管理，所有启动逻辑由UnifiedStartupManager处理 */
class SplashViewModel : BaseActivityViewModel() {

    private val _initState = MutableStateFlow(InitState.Loading)
    val initState = _initState.asStateFlow()

    /** 启动初始化流程 */
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

    /** 等待启动完成 */
    private suspend fun waitForStartupCompletion() {
        // 确保splash页面至少显示1.5秒，给用户良好的视觉体验
        val startTime = System.currentTimeMillis()
        val minSplashTime = 1500L // 最少显示1.5秒

        // 等待必要的初始化完成（用户就绪状态）
        while (
            UnifiedStartupManager.startupState.value !=
                UnifiedStartupManager.StartupState.UserReady &&
                UnifiedStartupManager.startupState.value !=
                    UnifiedStartupManager.StartupState.Completed
        ) {
            kotlinx.coroutines.delay(50) // 50ms检查一次，更快响应
        }

        EasyLog.log("SplashViewModel - 用户状态就绪，开始等待关键数据预加载")

        // 等待关键数据预加载完成（recommend agents）
        val maxWaitTime = 5000L // 最多等待5秒
        val dataWaitStartTime = System.currentTimeMillis()

        while (
            UnifiedStartupManager.getCurrentRecommendedAgents().isEmpty() &&
                (System.currentTimeMillis() - dataWaitStartTime) < maxWaitTime
        ) {
            kotlinx.coroutines.delay(100) // 100ms检查一次
        }

        val dataWaitTime = System.currentTimeMillis() - dataWaitStartTime
        if (UnifiedStartupManager.getCurrentRecommendedAgents().isNotEmpty()) {
            EasyLog.log("SplashViewModel - 关键数据预加载完成，耗时: ${dataWaitTime}ms")
        } else {
            EasyLog.log("SplashViewModel - 关键数据预加载超时，耗时: ${dataWaitTime}ms", EasyLog.WARN)
        }

        // 计算已经过去的时间
        val elapsedTime = System.currentTimeMillis() - startTime
        val remainingTime = minSplashTime - elapsedTime

        // 如果还没到最少显示时间，继续等待
        if (remainingTime > 0) {
            EasyLog.log("SplashViewModel - 数据预加载完成，等待splash显示时间: ${remainingTime}ms")
            kotlinx.coroutines.delay(remainingTime)
        }

        EasyLog.log("SplashViewModel - 启动完成，总耗时: ${System.currentTimeMillis() - startTime}ms")
    }
}
