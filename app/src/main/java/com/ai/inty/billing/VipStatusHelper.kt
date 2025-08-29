package com.ai.inty.billing

import android.app.Activity
import com.inty.utils.log.EasyLog

/**
 * VIP状态检查工具类
 * 统一管理VIP状态检查和购买逻辑
 */
object VipStatusHelper {

    /**
     * 检查用户是否为VIP
     */
    fun isUserVip(): Boolean {
        return BillingRepository.vipStatusFlow.value.isSubscribed
    }

    /**
     * 获取当前VIP状态
     */
    fun getVipStatus(): VipStatus {
        return BillingRepository.vipStatusFlow.value
    }

    /**
     * 检查VIP状态并执行相应操作
     */
    fun checkVipStatus(
        onVip: () -> Unit,
        onNotVip: () -> Unit
    ) {
        if (isUserVip()) {
            onVip()
        } else {
            onNotVip()
        }
    }

    /**
     * 统一的购买逻辑 - 购买第一个可用计划
     */
    fun purchaseFirstVip(activity: Activity, onError: (String) -> Unit = {}) {
        val currentPlans = BillingRepository.plansFlow.value
        if (currentPlans.isNotEmpty()) {
            val selectedPlan = currentPlans[0]
            EasyLog.log("VipStatusHelper - 准备购买订阅计划: ${selectedPlan.name} (${selectedPlan.googleProductId}) - ${selectedPlan.price}")

            // 检查用户是否已经订阅
            if (isUserVip()) {
                EasyLog.log("VipStatusHelper - 用户已经是订阅用户，无需重复购买", EasyLog.WARN)
                onError("用户已经是订阅用户")
                return
            }

            // 启动购买流程
            BillingRepository.launchBillingFlow(activity, selectedPlan.googleProductId)
        } else {
            EasyLog.log("VipStatusHelper - 无可用会员订阅计划", EasyLog.WARN)
            onError("无可用订阅计划")
        }
    }

    /**
     * 购买指定计划
     */
    fun purchasePlan(activity: Activity, productId: String, onError: (String) -> Unit = {}) {
        // 检查用户是否已经订阅
        if (isUserVip()) {
            EasyLog.log("VipStatusHelper - 用户已经是订阅用户，无需重复购买", EasyLog.WARN)
            onError("用户已经是订阅用户")
            return
        }

        // 检查计划是否存在
        val currentPlans = BillingRepository.plansFlow.value
        val planExists = currentPlans.any { it.googleProductId == productId }

        if (!planExists) {
            EasyLog.log("VipStatusHelper - 指定的计划不存在: $productId", EasyLog.WARN)
            onError("指定的计划不存在")
            return
        }

        // 启动购买流程
        BillingRepository.launchBillingFlow(activity, productId)
    }

    /**
     * 检查VIP状态并显示相应UI
     */
    fun checkVipStatusForUI(
        onVipAction: () -> Unit,
        onNotVipAction: () -> Unit,
        showPremiumDialog: () -> Unit = {}
    ) {
        checkVipStatus(
            onVip = onVipAction,
            onNotVip = {
                showPremiumDialog()
                onNotVipAction()
            }
        )
    }

    /**
     * 刷新订阅状态
     */
    fun refreshSubscriptionStatus() {
        BillingRepository.refreshSubscriptionStatus()
    }

    /**
     * 获取订阅计划列表
     */
    fun getPlans(): List<VipPlan> {
        return BillingRepository.plansFlow.value
    }

    /**
     * 检查是否有可用计划
     */
    fun hasAvailablePlans(): Boolean {
        return BillingRepository.plansFlow.value.isNotEmpty()
    }
}
