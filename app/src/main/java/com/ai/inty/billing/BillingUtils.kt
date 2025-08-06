package com.ai.inty.billing

import com.inty.utils.log.EasyLog

/**
 * 计费工具类
 */
object BillingUtils {

    /**
     * 检查是否为模拟器
     */
    fun isEmulator(): Boolean {
        return (android.os.Build.FINGERPRINT.startsWith("generic")
                || android.os.Build.FINGERPRINT.startsWith("unknown")
                || android.os.Build.MODEL.contains("google_sdk")
                || android.os.Build.MODEL.contains("Emulator")
                || android.os.Build.MODEL.contains("Android SDK built for x86")
                || android.os.Build.MANUFACTURER.contains("Genymotion")
                || (android.os.Build.BRAND.startsWith("generic") && android.os.Build.DEVICE.startsWith(
            "generic"
        ))
                || "google_sdk" == android.os.Build.PRODUCT)
    }

    /**
     * 根据货币代码修正货币符号
     */
    fun correctCurrencySymbol(price: String, currencyCode: String): String {
        val numberPart = price.filter { it.isDigit() || it == '.' }

        return when (currencyCode) {
            "TWD" -> "NT$$numberPart"
            "USD" -> "$$numberPart"
            "EUR" -> "€$numberPart"
            "JPY" -> "¥$numberPart"
            "CNY" -> "¥$numberPart"
            "GBP" -> "£$numberPart"
            "KRW" -> "₩$numberPart"
            "SGD" -> "S$$numberPart"
            "HKD" -> "HK$$numberPart"
            else -> price // 如果不知道货币代码，保持原样
        }
    }

    /**
     * 检查计划列表是否有关键字段变化
     */
    fun checkPlansChanged(currentPlans: List<VipPlan>, newPlans: List<VipPlan>): Boolean {
        // 如果数量不同，肯定有变化
        if (currentPlans.size != newPlans.size) {
            EasyLog.log("计划数量变化: ${currentPlans.size} -> ${newPlans.size}")
            return true
        }

        // 逐个比较计划
        for (i in currentPlans.indices) {
            val current = currentPlans[i]
            val new = newPlans[i]

            // 检查关键字段是否变化
            if (current.googleProductId != new.googleProductId ||
                current.discountRate != new.discountRate ||
                current.planType != new.planType ||
                current.description != new.description
            ) {
                EasyLog.log("检测到计划变化:")
                EasyLog.log("  googleProductId: ${current.googleProductId} -> ${new.googleProductId}")
                EasyLog.log("  discountRate: ${current.discountRate} -> ${new.discountRate}")
                EasyLog.log("  planType: ${current.planType} -> ${new.planType}")
                EasyLog.log("  description: ${current.description} -> ${new.description}")
                return true
            }
        }

        EasyLog.log("所有计划的关键字段都无变化")
        return false
    }
} 
