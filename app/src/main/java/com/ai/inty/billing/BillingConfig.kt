package com.ai.inty.billing

/**
 * 订阅配置类
 * 用于管理所有订阅相关的配置信息
 */
object BillingConfig {
    /**
     * 订阅产品 ID 列表
     * 当产品经理提供订阅 ID 后，在这里添加
     * 格式：产品ID -> 产品描述
     */
    val SUBSCRIPTION_IDS: Map<String, String> = mapOf(
        // 示例格式，等产品经理提供后替换
        // "com.ai.inty.subscription.monthly" to "月度订阅",
        // "com.ai.inty.subscription.yearly" to "年度订阅",
    )

    /**
     * 获取所有订阅 ID 列表
     */
    fun getSubscriptionIds(): List<String> = SUBSCRIPTION_IDS.keys.toList()

    /**
     * 获取订阅产品描述
     */
    fun getSubscriptionDescription(id: String): String = SUBSCRIPTION_IDS[id] ?: id
} 