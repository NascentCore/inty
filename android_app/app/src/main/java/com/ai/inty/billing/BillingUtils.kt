package com.ai.inty.billing

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.google.android.gms.common.GoogleApiAvailability

/** 计费工具类 */
internal object BillingUtils {

    /** 检查Google Play服务是否可用 */
    fun isGooglePlayServicesAvailable(context: Context): Boolean {
        val googleApiAvailability = GoogleApiAvailability.getInstance()
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

        LogUtils.i("BillingRepository BillingUtils - Google Play 服务检查结果: $resultCode")

        when (resultCode) {
            com.google.android.gms.common.ConnectionResult.SUCCESS -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务可用")
                return true
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_MISSING -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务缺失")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务版本过低")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_DISABLED -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务被禁用")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_INVALID -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务无效")
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_UPDATING -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务正在更新")
            }

            com.google.android.gms.common.ConnectionResult.TIMEOUT -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务连接超时")
            }

            com.google.android.gms.common.ConnectionResult.INTERRUPTED -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务连接被中断")
            }

            com.google.android.gms.common.ConnectionResult.INVALID_ACCOUNT -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 账户无效")
            }

            com.google.android.gms.common.ConnectionResult.RESOLUTION_REQUIRED -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务需要用户操作解决")
            }

            else -> {
                LogUtils.i("BillingRepository BillingUtils - Google Play 服务不可用，错误码: $resultCode")
            }
        }

        return false
    }

    /** 根据货币代码修正货币符号 */
    fun correctCurrencySymbol(price: String, currencyCode: String): String {
        val numberPart = price.filter { it.isDigit() || it == '.' }

        // 删除小数点后的 .00
        val formattedNumberPart =
            if (numberPart.endsWith(".00")) {
                numberPart.dropLast(3)
            } else {
                numberPart
            }

        return when (currencyCode) {
            "TWD" -> "NT$$formattedNumberPart"
            "USD" -> "$$formattedNumberPart"
            "EUR" -> "€$formattedNumberPart"
            "JPY" -> "¥$formattedNumberPart"
            "CNY" -> "¥$formattedNumberPart"
            "GBP" -> "£$formattedNumberPart"
            "KRW" -> "₩$formattedNumberPart"
            "SGD" -> "S$$formattedNumberPart"
            "HKD" -> "HK$$formattedNumberPart"
            else -> price // 如果不知道货币代码，保持原样
        }
    }
}
