package ai.sxwl.android.utils

import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ResolveInfo
import android.util.Log
import androidx.core.net.toUri

/** 应用商店工具类 提供应用商店相关的工具方法 */
object AppStoreUtils {

    private const val TAG = "AppStoreUtils"
    private const val GOOGLE_PLAY_PACKAGE = "com.android.vending"
    private const val SAMSUNG_APPS_PACKAGE = "com.sec.android.app.samsungapps"

    /** 应用商店配置 */
    data class AppStoreConfig(
        val packageName: String = Utils.getApp()?.packageName ?: "",
        val includeGooglePlay: Boolean = false,
        val preferredStore: String? = null
    )

    /**
     * 获取跳转到应用商店的 Intent
     *
     * @param config 应用商店配置
     * @return Intent 对象，如果无法获取则返回 null
     */
    fun getAppStoreIntent(config: AppStoreConfig = AppStoreConfig()): Intent? {
        return try {
            // 检查packageName是否有效
            if (config.packageName.isBlank()) {
                Log.w(TAG, "packageName为空，无法获取应用商店Intent")
                return null
            }

            when {
                RomUtils.isSamsung() -> getSamsungAppStoreIntent(config.packageName)
                else -> getGenericAppStoreIntent(config)
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取应用商店Intent失败", e)
            null
        }
    }

    /** 便捷方法：获取当前应用的应用商店Intent */
    fun getCurrentAppStoreIntent(includeGooglePlay: Boolean = false): Intent? {
        return getAppStoreIntent(AppStoreConfig(includeGooglePlay = includeGooglePlay))
    }

    /** 便捷方法：获取指定应用的应用商店Intent */
    fun getAppStoreIntent(packageName: String, includeGooglePlay: Boolean = false): Intent? {
        return getAppStoreIntent(AppStoreConfig(packageName, includeGooglePlay))
    }

    /** 获取通用应用商店Intent */
    private fun getGenericAppStoreIntent(config: AppStoreConfig): Intent? {
        val intent =
            Intent().apply {
                data = "market://details?id=${config.packageName}".toUri()
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

        val app = Utils.getApp() ?: return null
        val packageManager = app.packageManager ?: return null

        val resolveInfos: List<ResolveInfo>? =
            try {
                packageManager.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY)
            } catch (e: Exception) {
                Log.e(TAG, "查询Intent活动失败", e)
                return null
            }

        if (resolveInfos.isNullOrEmpty()) {
            Log.w(TAG, "未找到可用的应用商店")
            return null
        }

        // 优先选择系统应用商店
        for (resolveInfo in resolveInfos) {
            val activityInfo = resolveInfo.activityInfo ?: continue
            val pkgName = activityInfo.packageName ?: continue

            try {
                if (pkgName != GOOGLE_PLAY_PACKAGE && AppUtils.isAppSystem(pkgName)) {
                    intent.setPackage(pkgName)
                    return intent
                }
            } catch (e: Exception) {
                Log.w(TAG, "检查应用商店系统状态失败: $pkgName", e)
                continue
            }
        }

        // 如果包含Google Play且找到Google Play
        if (config.includeGooglePlay) {
            val googlePlayInfo =
                resolveInfos.find { it.activityInfo?.packageName == GOOGLE_PLAY_PACKAGE }
            if (googlePlayInfo != null) {
                intent.setPackage(GOOGLE_PLAY_PACKAGE)
                return intent
            }
        }

        // 使用第一个可用的应用商店
        val firstResolveInfo = resolveInfos.firstOrNull()
        val firstActivityInfo = firstResolveInfo?.activityInfo
        val firstPackageName = firstActivityInfo?.packageName

        if (firstPackageName != null) {
            intent.setPackage(firstPackageName)
            return intent
        }

        Log.w(TAG, "没有可用的应用商店")
        return null
    }

    /** 获取三星应用商店Intent */
    private fun getSamsungAppStoreIntent(packageName: String): Intent? {
        if (packageName.isBlank()) {
            Log.w(TAG, "packageName为空，无法获取三星应用商店Intent")
            return null
        }

        val intent =
            Intent().apply {
                setClassName(SAMSUNG_APPS_PACKAGE, "com.sec.android.app.samsungapps.Main")
                data = "http://www.samsungapps.com/appquery/appDetail.as?appId=$packageName".toUri()
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        return intent.takeIf { isIntentAvailable(it) }
    }

    /** 检查Intent是否可用 */
    private fun isIntentAvailable(intent: Intent): Boolean {
        return try {
            val app = Utils.getApp() ?: return false
            val packageManager = app.packageManager ?: return false

            packageManager
                .queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY)
                .isNotEmpty()
        } catch (e: Exception) {
            Log.e(TAG, "检查Intent可用性失败", e)
            false
        }
    }

    /** 获取可用的应用商店列表 */
    fun getAvailableAppStores(): List<String> {
        val intent =
            Intent().apply {
                data = "market://details?id=test".toUri()
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

        return try {
            val app = Utils.getApp() ?: return emptyList()
            val packageManager = app.packageManager ?: return emptyList()

            packageManager
                .queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY)
                .mapNotNull { resolveInfo -> resolveInfo.activityInfo?.packageName }
        } catch (e: Exception) {
            Log.e(TAG, "获取可用应用商店失败", e)
            emptyList()
        }
    }
}
