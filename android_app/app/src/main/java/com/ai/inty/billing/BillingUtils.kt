package com.ai.inty.billing

import android.content.Context
import com.google.android.gms.common.GoogleApiAvailability
import com.inty.utils.log.EasyLog

/**
 * 计费工具类
 */
internal object BillingUtils {

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
     * 检查Google Play服务是否可用
     */
    fun isGooglePlayServicesAvailable(context: Context): Boolean {
        val googleApiAvailability = GoogleApiAvailability.getInstance()
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

        EasyLog.log("BillingRepository BillingUtils - Google Play 服务检查结果: $resultCode")

        when (resultCode) {
            com.google.android.gms.common.ConnectionResult.SUCCESS -> {
                EasyLog.log("BillingRepository BillingUtils - Google Play 服务可用")
                return true
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_MISSING -> {
                EasyLog.log("BillingRepository BillingUtils - Google Play 服务缺失")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                EasyLog.log("BillingRepository BillingUtils - Google Play 服务版本过低")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_DISABLED -> {
                EasyLog.log("BillingRepository BillingUtils - Google Play 服务被禁用")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_INVALID -> {
                EasyLog.log("BillingRepository BillingUtils - Google Play 服务无效")
            }

            else -> {
                EasyLog.log("BillingRepository BillingUtils - Google Play 服务不可用，错误码: $resultCode")
            }
        }

        return false
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
} 
