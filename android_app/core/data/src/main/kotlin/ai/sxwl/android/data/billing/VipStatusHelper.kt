package ai.sxwl.android.data.billing

import ai.sxwl.android.utils.LogUtils
import android.app.Activity

/**
 * VIP状态检查工具类
 * 统一管理VIP状态检查和购买逻辑
 *
 * 职责：
 * - 简化VIP状态检查
 * - 统一购买流程
 * - 业务逻辑封装
 * - 错误处理
 */
object VipStatusHelper {

    /** 查询用户是否为VIP */
    fun isUserVip(): Boolean {
        return BillingRepository.vipStatusFlow.value.isSubscribed
    }

    /** 获取当前VIP状态 */
    fun getVipStatus(): VipStatus {
        return BillingRepository.vipStatusFlow.value
    }

    /** 检查VIP状态并执行相应操作 */
    fun checkVipStatus(onVip: () -> Unit, onNotVip: () -> Unit) {
        if (isUserVip()) {
            onVip()
        } else {
            onNotVip()
        }
    }

    /** 统一的购买逻辑 - 购买第一个可用计划 */
    fun purchaseFirstVip(activity: Activity, onError: (String) -> Unit = {}) {
        val currentPlans = BillingRepository.plansFlow.value
        if (currentPlans.isNotEmpty()) {
            val selectedPlan = currentPlans[0]
// 检查用户是否已经订阅
            if (isUserVip()) {
                LogUtils.w("VipStatusHelper - 用户已经是订阅用户，无需重复购买")
                onError("用户已经是订阅用户")
                return
            }
// 启动购买流程
            BillingRepository.launchBillingFlow(activity, selectedPlan.googleProductId)
        } else {
            LogUtils.w("VipStatusHelper - 无可用会员订阅计划")
            onError("无可用订阅计划")
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
