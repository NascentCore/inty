package com.ai.inty.billing

import com.inty.utils.storage.IntySetting
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * 远程订阅配置数据类
 */
data class RemoteBillingConfig(
    val subscriptionIds: Map<String, String>,
    val version: String,
    val enabled: Boolean = true,
    val updateTime: Long = System.currentTimeMillis()
)

/**
 * 订阅配置管理类
 * 支持远程配置和本地缓存，提高运营灵活性
 */
object BillingConfig {
    private const val KEY_BILLING_CONFIG = "billing_config"
    private const val KEY_CONFIG_VERSION = "billing_config_version"
    
    // 本地状态流
    private val _configState = MutableStateFlow<RemoteBillingConfig?>(null)
    val configState: StateFlow<RemoteBillingConfig?> = _configState.asStateFlow()
    
    // 默认配置（兜底方案）
    // 注意：商品ID必须是Google Play Console中配置的完整格式
    private val DEFAULT_SUBSCRIPTION_IDS = mapOf(
        "com.ai.inty.premium.monthly" to "Monthly",
        "com.ai.inty.premium.quarterly" to "Quarterly", 
        "com.ai.inty.premium.yearly" to "Yearly"
    )
    
    init {
        EasyLog.log("BillingConfig 初始化")
        EasyLog.log("默认商品ID (Google Play Console格式): ${DEFAULT_SUBSCRIPTION_IDS.keys}")
        EasyLog.log("应用包名: com.ai.inty")
        // loadLocalConfig()
    }
    

    
    // /**
    //  * 从本地存储加载配置
    //  */
    // private fun loadLocalConfig() {
    //     try {
    //         val configJson = IntySetting.getUserProfileData(KEY_BILLING_CONFIG) ?: ""
    //         if (configJson.isNotEmpty()) {
    //             // TODO: 使用 JSON 解析器解析配置
    //             // val config = Json.decodeFromString<RemoteBillingConfig>(configJson)
    //             // _configState.value = config
    //             EasyLog.log("加载本地订阅配置成功")
    //         }
    //     } catch (e: Exception) {
    //         EasyLog.log("加载本地订阅配置失败: ${e.message}")
    //     }
    // }
    
    /**
     * 更新远程配置
     */
    fun updateRemoteConfig(config: RemoteBillingConfig) {
        try {
            // 保存到本地存储
            // val configJson = Json.encodeToString(config)
            // IntySetting.setUserProfileData(KEY_BILLING_CONFIG, configJson)
            // IntySetting.setUserProfileData(KEY_CONFIG_VERSION, config.version)
            
            // 更新状态
            _configState.value = config
            EasyLog.log("更新远程订阅配置成功: ${config.subscriptionIds.size} 个商品")
        } catch (e: Exception) {
            EasyLog.log("更新远程订阅配置失败: ${e.message}")
        }
    }
    
    /**
     * 获取所有订阅 ID 列表
     * 优先级：远程配置 > 本地缓存 > 默认配置
     */
    fun getSubscriptionIds(): List<String> {
        val remoteIds = _configState.value?.subscriptionIds?.keys?.toList()
        val defaultIds = DEFAULT_SUBSCRIPTION_IDS.keys.toList()
        
        EasyLog.log("BillingConfig.getSubscriptionIds() - 远程配置: $remoteIds, 默认配置: $defaultIds")
        
        val result = remoteIds ?: defaultIds
        EasyLog.log("BillingConfig.getSubscriptionIds() - 最终返回: $result")
        
        return result
    }
    
    /**
     * 获取订阅产品描述
     */
    fun getSubscriptionDescription(id: String): String {
        return _configState.value?.subscriptionIds?.get(id) 
            ?: DEFAULT_SUBSCRIPTION_IDS[id] 
            ?: id
    }
    
    // /**
    //  * 检查配置是否启用
    //  */
    // fun isConfigEnabled(): Boolean {
    //     return _configState.value?.enabled ?: true
    // }
    
    // /**
    //  * 获取配置版本
    //  */
    // fun getConfigVersion(): String {
    //     return _configState.value?.version ?: "1.0.0"
    // }
    
    // /**
    //  * 强制刷新配置（用于调试）
    //  */
    // fun forceRefresh() {
    //     loadLocalConfig()
    // }
} 