package com.ai.inty.billing

import com.architecture.httplib.utils.MoshiUtils
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting

/** 计费本地存储管理类 */
internal object BillingStorage {

    private const val KEY_VIP_STATUS = "vip_status"
    private const val KEY_SUBSCRIPTION_PLANS = "subscription_plans"

    /** 保存本地会员状态 */
    fun saveLocalVipStatus(vipStatus: VipStatus) {
        try {
            val json = MoshiUtils.toJson(vipStatus)
            IntySetting.setUserProfileData(KEY_VIP_STATUS, json)
        } catch (e: Exception) {
            EasyLog.log(
                "BillingRepository BillingStorage 保存本地会员状态失败: ${e.message}",
                EasyLog.ERROR
            )
        }
    }

    /** 获取本地会员状态 */
    fun getLocalVipStatus(): VipStatus {
        val vipStatusStr = IntySetting.getUserProfileData(KEY_VIP_STATUS)
        return if (vipStatusStr.isNullOrEmpty()) {
            VipStatus(isSubscribed = false)
        } else {
            try {
                MoshiUtils.fromJson<VipStatus>(vipStatusStr) ?: VipStatus(isSubscribed = false)
            } catch (e: Exception) {
                EasyLog.log(
                    "BillingRepository BillingStorage 解析本地会员状态失败: ${e.message}",
                    EasyLog.ERROR
                )
                VipStatus(isSubscribed = false)
            }
        }
    }

    /** 保存本地订阅计划 */
    fun saveLocalPlans(plans: List<VipPlan>) {
        try {
            val type =
                com.squareup.moshi.Types.newParameterizedType(List::class.java, VipPlan::class.java)
            val adapter = MoshiUtils.moshiBuild.adapter<List<VipPlan>>(type)
            val json = adapter.toJson(plans) ?: ""
            IntySetting.setUserProfileData(KEY_SUBSCRIPTION_PLANS, json)
        } catch (e: Exception) {
            EasyLog.log("BillingRepository BillingStorage 保存本地订阅计划失败: ${e.message}")
        }
    }

    /** 获取本地订阅计划 */
    fun getLocalPlans(): List<VipPlan> {
        val plansStr = IntySetting.getUserProfileData(KEY_SUBSCRIPTION_PLANS)
        return if (plansStr.isNullOrEmpty()) {
            emptyList()
        } else {
            try {
                val type =
                    com.squareup.moshi.Types.newParameterizedType(
                        List::class.java,
                        VipPlan::class.java,
                    )
                val adapter = MoshiUtils.moshiBuild.adapter<List<VipPlan>>(type)
                adapter.fromJson(plansStr) ?: emptyList()
            } catch (e: Exception) {
                EasyLog.log("BillingRepository BillingStorage 解析本地订阅计划失败: ${e.message}")

                // 如果解析失败，清除损坏的缓存数据
                try {
                    IntySetting.setUserProfileData(KEY_SUBSCRIPTION_PLANS, "")
                } catch (clearException: Exception) {
                    EasyLog.log(
                        "BillingRepository BillingStorage 清除缓存数据失败: ${clearException.message}"
                    )
                }

                emptyList()
            }
        }
    }
}
