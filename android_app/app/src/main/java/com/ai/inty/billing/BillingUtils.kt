package com.ai.inty.billing

import android.content.Context
import com.google.android.gms.common.GoogleApiAvailability
import com.inty.utils.log.EasyLog

/** 计费工具类 */
internal object BillingUtils {

  /** 检查是否为模拟器 */
  fun isEmulator(): Boolean {
    return (android.os.Build.FINGERPRINT.startsWith("generic") ||
        android.os.Build.FINGERPRINT.startsWith("unknown") ||
        android.os.Build.MODEL.contains("google_sdk") ||
        android.os.Build.MODEL.contains("Emulator") ||
        android.os.Build.MODEL.contains("Android SDK built for x86") ||
        android.os.Build.MANUFACTURER.contains("Genymotion") ||
        (android.os.Build.BRAND.startsWith("generic") &&
            android.os.Build.DEVICE.startsWith("generic")) ||
        "google_sdk" == android.os.Build.PRODUCT)
  }

  /** 检查Google Play服务是否可用 */
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

      com.google.android.gms.common.ConnectionResult.SERVICE_UPDATING -> {
        EasyLog.log("BillingRepository BillingUtils - Google Play 服务正在更新")
      }

      com.google.android.gms.common.ConnectionResult.TIMEOUT -> {
        EasyLog.log("BillingRepository BillingUtils - Google Play 服务连接超时")
      }

      com.google.android.gms.common.ConnectionResult.INTERRUPTED -> {
        EasyLog.log("BillingRepository BillingUtils - Google Play 服务连接被中断")
      }

      com.google.android.gms.common.ConnectionResult.INVALID_ACCOUNT -> {
        EasyLog.log("BillingRepository BillingUtils - Google Play 账户无效")
      }

      com.google.android.gms.common.ConnectionResult.RESOLUTION_REQUIRED -> {
        EasyLog.log("BillingRepository BillingUtils - Google Play 服务需要用户操作解决")
      }

      else -> {
        EasyLog.log("BillingRepository BillingUtils - Google Play 服务不可用，错误码: $resultCode")
      }
    }

    return false
  }

  /** 获取Google Play服务错误的详细描述 */
  fun getGooglePlayServicesErrorDescription(context: Context): String {
    val googleApiAvailability = GoogleApiAvailability.getInstance()
    val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

    return when (resultCode) {
      com.google.android.gms.common.ConnectionResult.SUCCESS -> "Google Play 服务正常"
      com.google.android.gms.common.ConnectionResult.SERVICE_MISSING -> "Google Play 服务未安装"
      com.google.android.gms.common.ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED ->
          "Google Play 服务版本过低，需要更新"
      com.google.android.gms.common.ConnectionResult.SERVICE_DISABLED -> "Google Play 服务被禁用"
      com.google.android.gms.common.ConnectionResult.SERVICE_INVALID -> "Google Play 服务无效"
      com.google.android.gms.common.ConnectionResult.SERVICE_UPDATING -> "Google Play 服务正在更新"
      com.google.android.gms.common.ConnectionResult.TIMEOUT -> "Google Play 服务连接超时"
      com.google.android.gms.common.ConnectionResult.INTERRUPTED -> "Google Play 服务连接被中断"
      com.google.android.gms.common.ConnectionResult.INVALID_ACCOUNT -> "Google Play 账户无效"
      com.google.android.gms.common.ConnectionResult.RESOLUTION_REQUIRED -> "Google Play 服务需要用户操作解决"
      else -> "Google Play 服务不可用 (错误码: $resultCode)"
    }
  }

  /** 根据货币代码修正货币符号 */
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
