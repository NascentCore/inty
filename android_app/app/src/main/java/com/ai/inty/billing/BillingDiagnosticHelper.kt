package com.ai.inty.billing

import android.content.Context
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import com.google.android.gms.common.GoogleApiAvailability
import com.inty.utils.log.EasyLog
import java.security.MessageDigest

/**
 * Billing诊断工具类
 * 用于诊断BILLING_UNAVAILABLE等问题
 */
object BillingDiagnosticHelper {

    /**
     * 执行完整的billing诊断
     */
    fun performBillingDiagnostic(context: Context): BillingDiagnosticReport {
        EasyLog.log("BillingDiagnosticHelper - 开始执行billing诊断")

        // 1. 检查Google Play服务
        val googlePlayServicesStatus = checkGooglePlayServices(context)

        // 2. 检查应用签名
        val appSignatureInfo = getAppSignatureInfo(context)

        // 3. 检查应用配置
        val appConfigInfo = getAppConfigInfo(context)

        // 4. 检查设备信息
        val deviceInfo = getDeviceInfo()

        // 5. 检查网络连接
        val networkInfo = getNetworkInfo(context)

        // 6. 检查BillingRepository状态
        val billingRepositoryStatus = getBillingRepositoryStatus()

        val report = BillingDiagnosticReport(
            googlePlayServicesStatus = googlePlayServicesStatus,
            appSignatureInfo = appSignatureInfo,
            appConfigInfo = appConfigInfo,
            deviceInfo = deviceInfo,
            networkInfo = networkInfo,
            billingRepositoryStatus = billingRepositoryStatus
        )

        EasyLog.log("BillingDiagnosticHelper - billing诊断完成")
        EasyLog.log("BillingDiagnosticHelper - 诊断报告: $report")

        return report
    }

    private fun checkGooglePlayServices(context: Context): GooglePlayServicesStatus {
        val googleApiAvailability = GoogleApiAvailability.getInstance()
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)

        return when (resultCode) {
            com.google.android.gms.common.ConnectionResult.SUCCESS -> {
                GooglePlayServicesStatus.AVAILABLE
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_MISSING -> {
                GooglePlayServicesStatus.SERVICE_MISSING
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                GooglePlayServicesStatus.SERVICE_VERSION_UPDATE_REQUIRED
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_DISABLED -> {
                GooglePlayServicesStatus.SERVICE_DISABLED
            }

            com.google.android.gms.common.ConnectionResult.SERVICE_INVALID -> {
                GooglePlayServicesStatus.SERVICE_INVALID
            }

            else -> {
                GooglePlayServicesStatus.UNKNOWN_ERROR(resultCode)
            }
        }
    }

    private fun getAppSignatureInfo(context: Context): AppSignatureInfo {
        return try {
            val packageInfo: PackageInfo = context.packageManager.getPackageInfo(
                context.packageName,
                PackageManager.GET_SIGNATURES
            )

            val signatures = packageInfo.signatures
            val signature = signatures?.firstOrNull()

            if (signature != null) {
                val md = MessageDigest.getInstance("SHA-1")
                md.update(signature.toByteArray())
                val signatureHash = md.digest().joinToString("") { "%02x".format(it) }

                AppSignatureInfo(
                    signatureHash = signatureHash,
                    signatureCount = signatures.size,
                    isDebug = packageInfo.applicationInfo?.flags?.and(android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0
                )
            } else {
                AppSignatureInfo(
                    signatureHash = "NO_SIGNATURE",
                    signatureCount = 0,
                    isDebug = false
                )
            }
        } catch (e: Exception) {
            AppSignatureInfo(
                signatureHash = "ERROR: ${e.message}",
                signatureCount = 0,
                isDebug = false
            )
        }
    }

    private fun getAppConfigInfo(context: Context): AppConfigInfo {
        val packageInfo = context.packageManager.getPackageInfo(
            context.packageName,
            PackageManager.GET_META_DATA
        )

        val applicationInfo = context.applicationInfo

        // 检查应用安装来源
        val installerPackageName =
            context.packageManager.getInstallerPackageName(context.packageName)
        val installSource = when (installerPackageName) {
            "com.android.vending" -> "Google Play商店"
            null -> "直接安装"
            else -> "其他来源: $installerPackageName"
        }

        return AppConfigInfo(
            packageName = context.packageName,
            versionName = packageInfo.versionName ?: "unknown",
            versionCode = packageInfo.longVersionCode,
            isDebug = (applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0,
            targetSdk = applicationInfo.targetSdkVersion,
            minSdk = applicationInfo.minSdkVersion,
            installSource = installSource,
            canUseBilling = installerPackageName == "com.android.vending"
        )
    }

    private fun getDeviceInfo(): DeviceDiagnosticInfo {
        return DeviceDiagnosticInfo(
            manufacturer = android.os.Build.MANUFACTURER,
            model = android.os.Build.MODEL,
            androidVersion = android.os.Build.VERSION.RELEASE,
            apiLevel = android.os.Build.VERSION.SDK_INT,
            isEmulator = BillingUtils.isEmulator(),
            fingerprint = android.os.Build.FINGERPRINT,
            brand = android.os.Build.BRAND,
            product = android.os.Build.PRODUCT
        )
    }

    private fun getNetworkInfo(context: Context): NetworkInfo {
        val connectivityManager =
            context.getSystemService(Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
        val networkInfo = connectivityManager.activeNetworkInfo
        return NetworkInfo(
            isConnected = networkInfo?.isConnected == true,
            networkType = networkInfo?.typeName ?: "UNKNOWN",
            isWifi = networkInfo?.type == android.net.ConnectivityManager.TYPE_WIFI,
            isMobile = networkInfo?.type == android.net.ConnectivityManager.TYPE_MOBILE
        )
    }

    private fun getBillingRepositoryStatus(): BillingRepositoryDiagnosticStatus {
        return BillingRepositoryDiagnosticStatus(
            isInitialized = BillingRepository.isInitialized(),
            isConnected = BillingRepository.isConnected(),
            hasVipStatus = BillingRepository.vipStatusFlow.value.isSubscribed,
            plansCount = BillingRepository.plansFlow.value.size,
            plansInfo = BillingRepository.plansFlow.value.map {
                "ID:${it.googleProductId}, Name:${it.name}, Price:${it.price}"
            },
            connectionState = BillingRepository.getConnectionState()
        )
    }
}

/**
 * Billing诊断报告
 */
data class BillingDiagnosticReport(
    val googlePlayServicesStatus: GooglePlayServicesStatus,
    val appSignatureInfo: AppSignatureInfo,
    val appConfigInfo: AppConfigInfo,
    val deviceInfo: DeviceDiagnosticInfo,
    val networkInfo: NetworkInfo,
    val billingRepositoryStatus: BillingRepositoryDiagnosticStatus
) {
    override fun toString(): String {
        return """
            BillingDiagnosticReport {
                googlePlayServices: $googlePlayServicesStatus
                appSignature: $appSignatureInfo
                appConfig: $appConfigInfo
                deviceInfo: $deviceInfo
                networkInfo: $networkInfo
                billingRepositoryStatus: $billingRepositoryStatus
            }
        """.trimIndent()
    }
}

/**
 * Google Play服务状态
 */
sealed class GooglePlayServicesStatus {
    object AVAILABLE : GooglePlayServicesStatus()
    object SERVICE_MISSING : GooglePlayServicesStatus()
    object SERVICE_VERSION_UPDATE_REQUIRED : GooglePlayServicesStatus()
    object SERVICE_DISABLED : GooglePlayServicesStatus()
    object SERVICE_INVALID : GooglePlayServicesStatus()
    data class UNKNOWN_ERROR(val errorCode: Int) : GooglePlayServicesStatus()
}

/**
 * 应用签名信息
 */
data class AppSignatureInfo(
    val signatureHash: String,
    val signatureCount: Int,
    val isDebug: Boolean
)

/**
 * 应用配置信息
 */
data class AppConfigInfo(
    val packageName: String,
    val versionName: String,
    val versionCode: Long,
    val isDebug: Boolean,
    val targetSdk: Int,
    val minSdk: Int,
    val installSource: String,
    val canUseBilling: Boolean
)

/**
 * 设备诊断信息
 */
data class DeviceDiagnosticInfo(
    val manufacturer: String,
    val model: String,
    val androidVersion: String,
    val apiLevel: Int,
    val isEmulator: Boolean,
    val fingerprint: String,
    val brand: String,
    val product: String
)

/**
 * 网络信息
 */
data class NetworkInfo(
    val isConnected: Boolean,
    val networkType: String,
    val isWifi: Boolean,
    val isMobile: Boolean
)

/**
 * BillingRepository诊断状态
 */
data class BillingRepositoryDiagnosticStatus(
    val isInitialized: Boolean,
    val isConnected: Boolean,
    val hasVipStatus: Boolean,
    val plansCount: Int,
    val plansInfo: List<String>,
    val connectionState: String
)
