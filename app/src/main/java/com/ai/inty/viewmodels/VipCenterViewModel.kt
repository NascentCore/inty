package com.ai.inty.viewmodels

import android.app.Activity
import com.ai.inty.base.BaseViewModel
import com.ai.inty.billing.BillingRepository
import com.ai.inty.billing.VipPlan
import com.ai.inty.billing.VipStatus
import com.ai.inty.billing.VipStatusHelper
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * 会员中心ViewModel，管理订阅状态和计划信息。
 */
class VipCenterViewModel : BaseViewModel() {
    private val _selectedPlanIndex = MutableStateFlow(0)
    val selectedPlanIndex: StateFlow<Int> = _selectedPlanIndex.asStateFlow()

    // 会员状态Flow，从BillingRepository订阅
    val vipStatusFlow: StateFlow<VipStatus> = BillingRepository.vipStatusFlow

    // 订阅计划Flow，从BillingRepository订阅
    val plansFlow: StateFlow<List<VipPlan>> = BillingRepository.plansFlow

    /**
     * 选择订阅计划
     */
    fun selectPlan(index: Int) {
        val currentPlans = plansFlow.value
        if (index >= 0 && index < currentPlans.size) {
            _selectedPlanIndex.value = index
            val selectedPlan = currentPlans[index]
            EasyLog.log("BillingRepository VipViewModel 选择订阅计划: ${selectedPlan.name} (${selectedPlan.googleProductId})")
        }
    }

    /**
     * 购买选中的订阅计划
     */
    fun purchaseSelectedPlan(activity: Activity) {
        val selectedIndex = _selectedPlanIndex.value
        val currentPlans = plansFlow.value

        if (selectedIndex >= 0 && selectedIndex < currentPlans.size) {
            val selectedPlan = currentPlans[selectedIndex]
            VipStatusHelper.purchasePlan(activity, selectedPlan.googleProductId) { error ->
                showNetworkAwareError(error)
            }
        } else {
            showNetworkAwareError("Error VipPlan Index: $selectedIndex")
            EasyLog.log("BillingRepository VipViewModel 无效的计划索引: $selectedIndex")
        }
    }

    /**
     * 获取选中的订阅计划
     */
    fun getSelectedPlan(): VipPlan? {
        val selectedIndex = _selectedPlanIndex.value
        val currentPlans = plansFlow.value

        return if (selectedIndex >= 0 && selectedIndex < currentPlans.size) {
            currentPlans[selectedIndex]
        } else {
            null
        }
    }

    /**
     * 检查用户是否为会员
     */
    fun isUserSubscribed(): Boolean {
        return VipStatusHelper.isUserVip()
    }

    /**
     * 获取用户订阅信息
     */
    fun getUserSubscriptionInfo(): VipStatus {
        return VipStatusHelper.getVipStatus()
    }

    /**
     * 检查是否有选中的计划
     */
    fun hasSelectedPlan(): Boolean {
        val selectedIndex = _selectedPlanIndex.value
        val currentPlans = plansFlow.value
        return selectedIndex >= 0 && selectedIndex < currentPlans.size
    }
}
