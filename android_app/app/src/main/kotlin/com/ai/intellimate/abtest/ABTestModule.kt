package com.ai.intellimate.abtest

/**
 * AB 测试模块依赖注入管理
 * 遵循项目的依赖注入模式
 */
object ABTestModule {
    
    // 单例实例
    private val _abTestConfig: ABTestConfig by lazy { ABTestConfig() }
    private val _abTestManager: ABTestManager by lazy { ABTestManager(_abTestConfig) }
    
    // 公共访问器
    fun getABTestConfig(): ABTestConfig = _abTestConfig
    fun getABTestManager(): ABTestManager = _abTestManager
}