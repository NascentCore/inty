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

/** 会员中心ViewModel，管理订阅状态和计划信息。 */
class VipCenterViewModel : BaseViewModel() {
    private val _selectedPlanIndex = MutableStateFlow(0)
    val selectedPlanIndex: StateFlow<Int> = _selectedPlanIndex.asStateFlow()

    // 会员状态Flow，从BillingRepository订阅
    val vipStatusFlow: StateFlow<VipStatus> = BillingRepository.vipStatusFlow

    // 订阅计划Flow，从BillingRepository订阅
    val plansFlow: StateFlow<List<VipPlan>> = BillingRepository.plansFlow
    
// Billing 初始化状态Flow
val initStateFlow: StateFlow<com.ai.inty.billing.BillingInitState> = BillingRepository.initStateFlow

    /** 选择订阅计划 */
    fun selectPlan(index: Int) {
        val currentPlans = plansFlow.value
        if (index >= 0 && index < currentPlans.size) {
            _selectedPlanIndex.value = index
            val selectedPlan = currentPlans[index]
            EasyLog.log(
                "BillingRepository VipViewModel 选择订阅计划: ${selectedPlan.name} (${selectedPlan.googleProductId})"
            )
        }
    }

    /** 购买选中的订阅计划 */
    fun purchaseSelectedPlan(activity: Activity) {
val initState = initStateFlow.value

// 检查 billing 是否可用
if (!initState.hasGooglePlayServices || !initState.isConnected) {
    showNetworkAwareError("当前设备不支持 Google Play 计费功能，请联系客服了解订阅方式")
    return
}

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

    /** 检查是否有选中的计划 */
    fun hasSelectedPlan(): Boolean {
        val selectedIndex = _selectedPlanIndex.value
        val currentPlans = plansFlow.value
        return selectedIndex >= 0 && selectedIndex < currentPlans.size
    }
}
