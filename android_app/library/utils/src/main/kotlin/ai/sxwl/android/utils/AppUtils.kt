package ai.sxwl.android.utils

import android.app.Activity
import android.app.ActivityManager
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.content.pm.Signature
import android.graphics.drawable.Drawable
import android.net.Uri
import android.os.Build
import android.os.Process
import android.provider.Settings
import android.util.Log
import androidx.core.content.getSystemService
import androidx.core.content.pm.PackageInfoCompat
import java.security.MessageDigest
import kotlin.system.exitProcess

/** 应用工具类 提供应用相关的工具方法 */
object AppUtils {

    // ==================== 应用状态监听 ====================

    /** 注册应用状态变化监听器 */
    fun registerAppStatusChangedListener(listener: Utils.OnAppStatusChangedListener) {
        UtilsBridge.addOnAppStatusChangedListener(listener)
    }

    /** 注销应用状态变化监听器 */
    fun unregisterAppStatusChangedListener(listener: Utils.OnAppStatusChangedListener) {
        UtilsBridge.removeOnAppStatusChangedListener(listener)
    }

    // ==================== 应用信息查询 ====================

    /** 判断应用是否已安装 */
    fun isAppInstalled(packageName: String): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return try {
            val app = Utils.getApp() ?: return false
            val packageManager = app.packageManager ?: return false
            packageManager.getApplicationInfo(packageName, 0).enabled
        } catch (e: PackageManager.NameNotFoundException) {
            false
        } catch (e: Exception) {
            Log.e("AppUtils", "检查应用安装状态失败", e)
            false
        }
    }

    /** 判断是否为调试应用 */
    fun isAppDebug(packageName: String = Utils.getApp()?.packageName ?: ""): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return try {
            val app = Utils.getApp() ?: return false
            val pm = app.packageManager ?: return false
            val ai = pm.getApplicationInfo(packageName, 0)
            (ai.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        } catch (e: PackageManager.NameNotFoundException) {
            false
        } catch (e: Exception) {
            Log.e("AppUtils", "检查应用调试状态失败", e)
            false
        }
    }

    /** 判断是否为系统应用 */
    fun isAppSystem(packageName: String = Utils.getApp()?.packageName ?: ""): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return try {
            val app = Utils.getApp() ?: return false
            val pm = app.packageManager ?: return false
            val ai = pm.getApplicationInfo(packageName, 0)
            (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0
        } catch (e: PackageManager.NameNotFoundException) {
            false
        } catch (e: Exception) {
            Log.e("AppUtils", "检查应用系统状态失败", e)
            false
        }
    }

    /** 判断应用是否在前台 */
    fun isAppForeground(packageName: String = Utils.getApp()?.packageName ?: ""): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return try {
            packageName == UtilsBridge.getForegroundProcessName()
        } catch (e: Exception) {
            Log.e("AppUtils", "检查应用前台状态失败", e)
            false
        }
    }

    /** 判断应用是否正在运行 */
    fun isAppRunning(packageName: String): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false

        return try {
            val app = Utils.getApp() ?: return false
            val am = app.getSystemService<ActivityManager>() ?: return false

            val runningProcesses = am.runningAppProcesses.orEmpty()
            val isRunningInProcess =
                runningProcesses.any { processInfo ->
                    processInfo.processName == packageName &&
                        processInfo.importance <= ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND
                }
            if (isRunningInProcess) return true

            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
                @Suppress("DEPRECATION")
                val runningServices = am.getRunningServices(Int.MAX_VALUE)
                if (runningServices?.any { it.service.packageName == packageName } == true) {
                    return true
                }
            }

            false
        } catch (e: Exception) {
            Log.e("AppUtils", "检查应用运行状态失败", e)
            false
        }
    }

    // ==================== 应用启动控制 ====================

    /** 启动应用 */
    fun launchApp(packageName: String) {
        if (UtilsBridge.isSpace(packageName)) return

        try {
            val app = Utils.getApp() ?: return
            val packageManager = app.packageManager ?: return

            val launchIntent = packageManager.getLaunchIntentForPackage(packageName)
            if (launchIntent == null) {
                Log.e("AppUtils", "未找到启动Activity")
                return
            }
            app.startActivity(launchIntent)
        } catch (e: Exception) {
            Log.e("AppUtils", "启动应用失败", e)
        }
    }

    /** 重启应用 */
    fun relaunchApp(killProcess: Boolean = false) {
        try {
            val app = Utils.getApp() ?: return
            val packageManager = app.packageManager ?: return
            val packageName = app.packageName ?: return

            val intent = packageManager.getLaunchIntentForPackage(packageName)
            if (intent == null) {
                Log.e("AppUtils", "未找到启动Activity")
                return
            }

            intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_CLEAR_TASK
            )
            app.startActivity(intent)

            if (killProcess) {
                // 警告：强制杀死进程可能导致数据丢失
                Log.w("AppUtils", "强制杀死进程，可能导致数据丢失")
                Process.killProcess(Process.myPid())
                exitProcess(0)
            }
        } catch (e: Exception) {
            Log.e("AppUtils", "重启应用失败", e)
        }
    }

    /** 退出应用 */
    fun exitApp() {
        try {
            // 先尝试正常退出
            UtilsBridge.finishAllActivities()

            // 延迟退出，给Activity时间完成清理
            android.os
                .Handler(android.os.Looper.getMainLooper())
                .postDelayed(
                    {
                        try {
                            Log.w("AppUtils", "强制退出应用，可能导致数据丢失")
                            exitProcess(0)
                        } catch (e: Exception) {
                            Log.e("AppUtils", "强制退出失败", e)
                        }
                    },
                    100,
                )
        } catch (e: Exception) {
            Log.e("AppUtils", "退出应用失败", e)
        }
    }

    // ==================== 应用信息获取 ====================

    /** 获取应用包名 */
    fun getPackageName(): String = Utils.getApp()?.packageName ?: ""

    /** 获取应用名称 */
    fun getAppName(packageName: String = Utils.getApp()?.packageName ?: ""): String {
        if (UtilsBridge.isSpace(packageName)) return ""
        return try {
            val app = Utils.getApp() ?: return ""
            val pm = app.packageManager ?: return ""
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.applicationInfo?.loadLabel(pm)?.toString() ?: ""
        } catch (e: PackageManager.NameNotFoundException) {
            ""
        } catch (e: Exception) {
            Log.e("AppUtils", "获取应用名称失败", e)
            ""
        }
    }

    /** 获取应用版本名称 */
    fun getVersionName(packageName: String = Utils.getApp()?.packageName ?: ""): String {
        if (UtilsBridge.isSpace(packageName)) return ""
        return try {
            val app = Utils.getApp() ?: return ""
            val pm = app.packageManager ?: return ""
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.versionName ?: ""
        } catch (e: PackageManager.NameNotFoundException) {
            ""
        } catch (e: Exception) {
            Log.e("AppUtils", "获取应用版本名称失败", e)
            ""
        }
    }

    /** 获取应用版本号 */
    fun getVersionCode(packageName: String = Utils.getApp()?.packageName ?: ""): Int {
        if (UtilsBridge.isSpace(packageName)) return -1
          return try {
              val app = Utils.getApp() ?: return -1
              val pm = app.packageManager ?: return -1
              val pi = pm.getPackageInfo(packageName, 0)
              pi.versionCodeCompat()
        } catch (e: PackageManager.NameNotFoundException) {
            -1
        } catch (e: Exception) {
            Log.e("AppUtils", "获取应用版本号失败", e)
            -1
        }
    }

    /** 获取应用图标 */
    fun getAppIcon(packageName: String = Utils.getApp()?.packageName ?: ""): Drawable? {
        if (UtilsBridge.isSpace(packageName)) return null
        return try {
            val app = Utils.getApp() ?: return null
            val pm = app.packageManager ?: return null
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.applicationInfo?.loadIcon(pm)
        } catch (e: PackageManager.NameNotFoundException) {
            null
        } catch (e: Exception) {
            Log.e("AppUtils", "获取应用图标失败", e)
            null
        }
    }

    /** 获取应用路径 */
    fun getAppPath(packageName: String = Utils.getApp()?.packageName ?: ""): String {
        if (UtilsBridge.isSpace(packageName)) return ""
        return try {
            val app = Utils.getApp() ?: return ""
            val pm = app.packageManager ?: return ""
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.applicationInfo?.sourceDir ?: ""
        } catch (e: PackageManager.NameNotFoundException) {
            ""
        } catch (e: Exception) {
            Log.e("AppUtils", "获取应用路径失败", e)
            ""
        }
    }

    // ==================== 应用设置 ====================

    /** 打开应用详情设置 */
    fun openAppDetailsSettings(packageName: String = Utils.getApp()?.packageName ?: "") {
        if (UtilsBridge.isSpace(packageName)) return

        try {
            val app = Utils.getApp() ?: return
            val intent =
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.fromParts("package", packageName, null)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            app.startActivity(intent)
        } catch (e: Exception) {
            Log.e("AppUtils", "打开应用详情设置失败", e)
        }
    }

    /**
     * 打开应用详情设置（带回调）
     *
     * @deprecated startActivityForResult已废弃，建议使用Activity Result API
     */
    @Deprecated("startActivityForResult已废弃，建议使用Activity Result API")
    fun openAppDetailsSettings(
        activity: Activity,
        requestCode: Int,
        packageName: String = Utils.getApp()?.packageName ?: "",
    ) {
        if (UtilsBridge.isSpace(packageName)) return

        try {
            val intent =
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.fromParts("package", packageName, null)
                }
            activity.startActivityForResult(intent, requestCode)
        } catch (e: Exception) {
            Log.e("AppUtils", "打开应用详情设置失败", e)
        }
    }

    // ==================== 应用签名 ====================

    /** 获取应用签名 */
    fun getAppSignatures(
        packageName: String = Utils.getApp()?.packageName ?: ""
    ): Array<Signature>? {
        if (UtilsBridge.isSpace(packageName)) return null
        return try {
            val app = Utils.getApp() ?: return null
            val pm = app.packageManager ?: return null

              if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                  val pi = pm.getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES)
                  val signingInfo = pi.signingInfo
                  if (signingInfo?.hasMultipleSigners() == true) {
                      signingInfo.apkContentsSigners
                  } else {
                      signingInfo?.signingCertificateHistory
                  }
              } else {
                  getLegacySignatures(pm, packageName)
              }
        } catch (e: PackageManager.NameNotFoundException) {
            null
        } catch (e: Exception) {
            Log.e("AppUtils", "获取应用签名失败", e)
            null
        }
    }

    /** 获取应用签名SHA1值 */
    fun getAppSignatureSHA1(packageName: String = Utils.getApp()?.packageName ?: ""): String? {
        val signatures = getAppSignatures(packageName) ?: return null
        return signatures.firstOrNull()?.let { signature ->
            try {
                val md = MessageDigest.getInstance("SHA1")
                md.update(signature.toByteArray())
                UtilsBridge.bytes2HexString(md.digest())
            } catch (e: Exception) {
                Log.e("AppUtils", "计算签名SHA1失败", e)
                null
            }
        }
    }

    // ==================== 应用信息数据类 ====================

    /** 应用信息数据类 */
    data class AppInfo(
        val packageName: String,
        val name: String,
        val icon: Drawable?,
        val versionName: String,
        val versionCode: Int,
        val isSystem: Boolean,
        val isDebug: Boolean,
    ) {
        override fun toString(): String {
            return "AppInfo{" +
                "packageName='$packageName', " +
                "name='$name', " +
                "versionName='$versionName', " +
                "versionCode=$versionCode, " +
                "isSystem=$isSystem, " +
                "isDebug=$isDebug" +
                "}"
        }
    }

    /** 获取应用信息 */
    fun getAppInfo(packageName: String = Utils.getApp()?.packageName ?: ""): AppInfo? {
        if (UtilsBridge.isSpace(packageName)) return null

        return try {
            val app = Utils.getApp() ?: return null
            val pm = app.packageManager ?: return null
            val pi = pm.getPackageInfo(packageName, 0)
            pi.applicationInfo?.let { ai ->
                AppInfo(
                    packageName = packageName,
                    name = ai.loadLabel(pm).toString(),
                    icon = ai.loadIcon(pm),
                    versionName = pi.versionName ?: "",
                    versionCode = pi.versionCodeCompat(),
                    isSystem = (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0,
                    isDebug = (ai.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0,
                )
            }
        } catch (e: PackageManager.NameNotFoundException) {
            null
        } catch (e: Exception) {
            Log.e("AppUtils", "获取应用信息失败", e)
            null
        }
    }

    /** 获取所有已安装应用信息 */
    fun getAllAppInfo(): List<AppInfo> {
        return try {
            val app = Utils.getApp() ?: return emptyList()
            val pm = app.packageManager ?: return emptyList()
            val installedPackages = pm.getInstalledPackages(0)

            installedPackages.mapNotNull { pi ->
                try {
                    pi.applicationInfo?.let { ai ->
                        AppInfo(
                            packageName = pi.packageName,
                            name = ai.loadLabel(pm).toString(),
                            icon = ai.loadIcon(pm),
                            versionName = pi.versionName ?: "",
                            versionCode = pi.versionCodeCompat(),
                            isSystem = (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0,
                            isDebug = (ai.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0,
                        )
                    }
                } catch (e: Exception) {
                    Log.w("AppUtils", "处理应用信息失败: ${pi.packageName}", e)
                    null
                }
            }
        } catch (e: Exception) {
            Log.e("AppUtils", "获取所有应用信息失败", e)
            emptyList()
        }
    }

    private fun PackageInfo.versionCodeCompat(): Int {
        val versionCode = PackageInfoCompat.getLongVersionCode(this)
        return versionCode.coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
    }

    private fun getLegacySignatures(
        pm: PackageManager,
        packageName: String,
    ): Array<Signature>? {
        @Suppress("DEPRECATION")
        val packageInfo = pm.getPackageInfo(packageName, PackageManager.GET_SIGNATURES)
        @Suppress("DEPRECATION") return packageInfo?.signatures
    }
}
