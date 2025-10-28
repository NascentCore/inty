package ai.sxwl.android.data.billing

import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.app.Activity

/**
 * VIP状态检查工具类 统一管理VIP状态检查和购买逻辑
 *
 * 职责：
 * - 简化VIP状态检查
 * - 统一购买流程
 * - 业务逻辑封装
 * - 错误处理
 */
object VipStatusHelper {

    /** 检查用户是否为VIP */
    fun isUserVip(): Boolean {
        return BillingRepository.vipStatusFlow.value.isSubscribed
    }

    /** 获取当前VIP状态 */
    fun getVipStatus(): VipStatus {
        return BillingRepository.vipStatusFlow.value
    }

    /** 获取订阅等级 */
    fun getSubscriptionLevel(): String {
        val vipStatus = getVipStatus()
        return when {
            vipStatus.isSubscribed -> "premium"
            vipStatus.everSubscribed -> "expired"
            else -> "free"
        }
    }

    /** 更新Firebase用户属性（VIP状态变化时调用） */
    fun updateFirebaseUserProperties() {
        try {
            val userType = if (isUserVip()) "vip" else "free"
            val subscriptionLevel = getSubscriptionLevel()

            FirebaseManager.setUserProperty(FirebaseManager.UserProperties.USER_TYPE, userType)
            FirebaseManager.setUserProperty(
                FirebaseManager.UserProperties.SUBSCRIPTION_LEVEL,
                subscriptionLevel
            )

            LogUtils.i(
                "VipStatusHelper - Firebase用户属性已更新: userType=$userType, subscriptionLevel=$subscriptionLevel"
            )
        } catch (e: Exception) {
            LogUtils.e("VipStatusHelper - 更新Firebase用户属性失败: ${e.message}")
        }
    }

    /** 购买指定计划 */
    fun purchasePlan(activity: Activity, productId: String, onError: (String) -> Unit = {}) {
        // 检查用户是否已经订阅
        if (isUserVip()) {
            LogUtils.w("VipStatusHelper - 用户已经是订阅用户，无需重复购买")
            onError("用户已经是订阅用户")
            return
        }

        // 检查计划是否存在
        val currentPlans = BillingRepository.plansFlow.value
        val planExists = currentPlans.any { it.googleProductId == productId }

        if (!planExists) {
            LogUtils.w("VipStatusHelper - 指定的计划不存在: $productId")
            onError("指定的计划不存在")
            return
        }

        // 启动购买流程
        BillingRepository.launchBillingFlow(activity, productId)
    }

    /** 刷新订阅状态 */
    fun refreshSubscriptionStatus() {
        BillingRepository.refreshSubscriptionStatus()
    }
}
