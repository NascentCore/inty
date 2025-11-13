package com.ai.intellimate.vip

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.billing.BillingEvent
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipPlan
import ai.sxwl.android.data.billing.VipStatus
import ai.sxwl.android.data.billing.VipStatusHelper
import ai.sxwl.android.utils.LogUtils
import android.app.Activity
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.utils.NetworkErrorHandler
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** 会员中心ViewModel，管理订阅状态和计划信息。 */
class VipCenterViewModel : BaseVM() {
    private val _selectedPlanIndex = MutableStateFlow(0)
    val selectedPlanIndex: StateFlow<Int> = _selectedPlanIndex.asStateFlow()

    // 购买loading状态
    private val _isPurchasing = MutableStateFlow(false)
    val isPurchasing: StateFlow<Boolean> = _isPurchasing.asStateFlow()

    // 会员状态Flow，从BillingRepository订阅
    val vipStatusFlow: StateFlow<VipStatus> = BillingRepository.vipStatusFlow

    // 订阅计划Flow，从BillingRepository订阅
    val plansFlow: StateFlow<List<VipPlan>> = BillingRepository.plansFlow

    init {
        // 监听 Billing 事件来更新 loading 状态
        viewModelScope.launch {
            BillingRepository.eventFlow.collect { event ->
                when (event) {
                    is BillingEvent.PurchaseSuccess -> {
                        _isPurchasing.value = false
                        LogUtils.d("VipCenterViewModel - 购买成功，停止 loading")
                    }

                    is BillingEvent.PurchaseFailed -> {
                        _isPurchasing.value = false
                        LogUtils.d("VipCenterViewModel - 购买失败，停止 loading")
                    }

                    is BillingEvent.UserCanceled -> {
                        _isPurchasing.value = false
                        LogUtils.d("VipCenterViewModel - 用户取消购买，停止 loading")
                    }

                    is BillingEvent.SkuDetailsQueryFailed -> {
                        // 如果是用户主动操作导致的查询失败，停止 loading
                        if (event.isUserInitiated) {
                            _isPurchasing.value = false
                            LogUtils.d("VipCenterViewModel - 商品查询失败（用户操作），停止 loading")
                        }
                    }

                    is BillingEvent.ShowError -> {
                        // 如果是用户主动操作导致的错误，停止 loading
                        if (event.isUserInitiated) {
                            _isPurchasing.value = false
                            LogUtils.d(
                                "VipCenterViewModel - 显示错误（用户操作），停止 loading: ${event.errorCode}"
                            )
                        }
                    }

                    else -> {
                        // 其他事件不影响 loading 状态
                    }
                }
            }
        }
    }

    /** 选择订阅计划 */
    fun selectPlan(index: Int) {
        val currentPlans = plansFlow.value
        if (index >= 0 && index < currentPlans.size) {
            _selectedPlanIndex.value = index
            val selectedPlan = currentPlans[index]
            LogUtils.d(
                "BillingRepository VipViewModel 选择订阅计划: ${selectedPlan.name} (${selectedPlan.googleProductId})"
            )
        }
    }

    /** 购买选中的订阅计划 */
    fun purchaseSelectedPlan(activity: Activity) {
        val selectedIndex = _selectedPlanIndex.value
        val currentPlans = plansFlow.value

        if (selectedIndex >= 0 && selectedIndex < currentPlans.size) {
            val selectedPlan = currentPlans[selectedIndex]
            // 开始购买流程，显示 loading
            _isPurchasing.value = true
            LogUtils.d("VipCenterViewModel - 开始购买流程，显示 loading")
            VipStatusHelper.purchasePlan(activity, selectedPlan.googleProductId) { error ->
                // 购买前置检查失败，停止 loading
                _isPurchasing.value = false
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
