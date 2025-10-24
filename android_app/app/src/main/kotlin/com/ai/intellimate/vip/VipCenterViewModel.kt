package com.ai.intellimate.vip

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipPlan
import ai.sxwl.android.data.billing.VipStatus
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.utils.LogUtils
import android.app.Activity
import com.ai.inty.utils.NetworkErrorHandler
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** 会员中心ViewModel，管理订阅状态和计划信息。 */
class VipCenterViewModel : BaseVM() {
    private val _selectedPlanIndex = MutableStateFlow(0)
    val selectedPlanIndex: StateFlow<Int> = _selectedPlanIndex.asStateFlow()

    // 会员状态Flow，从BillingRepository订阅
    val vipStatusFlow: StateFlow<VipStatus> = BillingRepository.vipStatusFlow

    // 订阅计划Flow，从BillingRepository订阅
    val plansFlow: StateFlow<List<VipPlan>> = BillingRepository.plansFlow

    /** 选择订阅计划 */
    fun selectPlan(index: Int) {
        val currentPlans = plansFlow.value
        if (index >= 0 && index < currentPlans.size) {
            _selectedPlanIndex.value = index
            val selectedPlan = currentPlans[index]
            LogUtils.d("BillingRepository VipViewModel 选择订阅计划: ${selectedPlan.name} (${selectedPlan.googleProductId})")
        }
    }

    /** 购买选中的订阅计划 */
    fun purchaseSelectedPlan(activity: Activity) {
        val selectedIndex = _selectedPlanIndex.value
        val currentPlans = plansFlow.value

        if (selectedIndex >= 0 && selectedIndex < currentPlans.size) {
            val selectedPlan = currentPlans[selectedIndex]
            VipStatusHelper.purchasePlan(activity, selectedPlan.googleProductId) { error ->
                NetworkErrorHandler.showNetworkAwareError(error)
            }
        } else {
            NetworkErrorHandler.showNetworkAwareError("Error VipPlan Index: $selectedIndex")
            LogUtils.i("BillingRepository VipViewModel 无效的计划索引: $selectedIndex")
        }
    }

    /** 检查是否有选中的计划 */
    fun hasSelectedPlan(): Boolean {
        val selectedIndex = _selectedPlanIndex.value
        val currentPlans = plansFlow.value
        return selectedIndex >= 0 && selectedIndex < currentPlans.size
    }
}
