package ai.sxwl.android.utils

import android.app.Activity
import android.app.ActivityManager
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.content.pm.Signature
import android.graphics.drawable.Drawable
import android.net.Uri
import android.os.Build
import android.os.Process
import android.provider.Settings
import android.util.Log
import androidx.core.content.getSystemService
import java.security.MessageDigest
import kotlin.system.exitProcess

/**
 * 应用工具类
 * 提供应用相关的工具方法
 */
object AppUtils {

    // ==================== 应用状态监听 ====================

    /**
     * 注册应用状态变化监听器
     */
    fun registerAppStatusChangedListener(listener: Utils.OnAppStatusChangedListener) {
        UtilsBridge.addOnAppStatusChangedListener(listener)
    }

    /**
     * 注销应用状态变化监听器
     */
    fun unregisterAppStatusChangedListener(listener: Utils.OnAppStatusChangedListener) {
        UtilsBridge.removeOnAppStatusChangedListener(listener)
    }

    // ==================== 应用信息查询 ====================

    /**
     * 判断应用是否已安装
     */
    fun isAppInstalled(packageName: String): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return try {
            Utils.getApp().packageManager.getApplicationInfo(packageName, 0).enabled
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }

    /**
     * 判断是否为调试应用
     */
    fun isAppDebug(packageName: String = Utils.getApp().packageName): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return try {
            val pm = Utils.getApp().packageManager
            val ai = pm.getApplicationInfo(packageName, 0)
            (ai.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }

    /**
     * 判断是否为系统应用
     */
    fun isAppSystem(packageName: String = Utils.getApp().packageName): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return try {
            val pm = Utils.getApp().packageManager
            val ai = pm.getApplicationInfo(packageName, 0)
            (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }

    /**
     * 判断应用是否在前台
     */
    fun isAppForeground(packageName: String = Utils.getApp().packageName): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false
        return packageName == UtilsBridge.getForegroundProcessName()
    }

    /**
     * 判断应用是否正在运行
     */
    fun isAppRunning(packageName: String): Boolean {
        if (UtilsBridge.isSpace(packageName)) return false

        val am = Utils.getApp().getSystemService<ActivityManager>() ?: return false

        // 检查运行的任务
        val runningTasks = am.getRunningTasks(Int.MAX_VALUE)
        if (runningTasks.any { it.baseActivity?.packageName == packageName }) {
            return true
        }

        // 检查运行的服务
        val runningServices = am.getRunningServices(Int.MAX_VALUE)
        return runningServices.any { it.service.packageName == packageName }
    }

    // ==================== 应用启动控制 ====================

    /**
     * 启动应用
     */
    fun launchApp(packageName: String) {
        if (UtilsBridge.isSpace(packageName)) return

        val launchIntent = Utils.getApp().packageManager.getLaunchIntentForPackage(packageName)
        if (launchIntent == null) {
            Log.e("AppUtils", "未找到启动Activity")
            return
        }
        Utils.getApp().startActivity(launchIntent)
    }

    /**
     * 重启应用
     */
    fun relaunchApp(killProcess: Boolean = false) {
        val intent =
            Utils.getApp().packageManager.getLaunchIntentForPackage(Utils.getApp().packageName)
        if (intent == null) {
            Log.e("AppUtils", "未找到启动Activity")
            return
        }

        intent.addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_CLEAR_TASK
        )
        Utils.getApp().startActivity(intent)

        if (killProcess) {
            Process.killProcess(Process.myPid())
            exitProcess(0)
        }
    }

    /**
     * 退出应用
     */
    fun exitApp() {
        UtilsBridge.finishAllActivities()
        exitProcess(0)
    }

    // ==================== 应用信息获取 ====================

    /**
     * 获取应用包名
     */
    fun getPackageName(): String = Utils.getApp().packageName

    /**
     * 获取应用名称
     */
    fun getAppName(packageName: String = Utils.getApp().packageName): String {
        if (UtilsBridge.isSpace(packageName)) return ""
        return try {
            val pm = Utils.getApp().packageManager
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.applicationInfo?.loadLabel(pm)?.toString() ?: ""
        } catch (e: PackageManager.NameNotFoundException) {
            ""
        }
    }

    /**
     * 获取应用版本名称
     */
    fun getVersionName(packageName: String = Utils.getApp().packageName): String {
        if (UtilsBridge.isSpace(packageName)) return ""
        return try {
            val pm = Utils.getApp().packageManager
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.versionName ?: ""
        } catch (e: PackageManager.NameNotFoundException) {
            ""
        }
    }

    /**
     * 获取应用版本号
     */
    fun getVersionCode(packageName: String = Utils.getApp().packageName): Int {
        if (UtilsBridge.isSpace(packageName)) return -1
        return try {
            val pm = Utils.getApp().packageManager
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.versionCode ?: -1
        } catch (e: PackageManager.NameNotFoundException) {
            -1
        }
    }

    /**
     * 获取应用图标
     */
    fun getAppIcon(packageName: String = Utils.getApp().packageName): Drawable? {
        if (UtilsBridge.isSpace(packageName)) return null
        return try {
            val pm = Utils.getApp().packageManager
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.applicationInfo?.loadIcon(pm)
        } catch (e: PackageManager.NameNotFoundException) {
            null
        }
    }

    /**
     * 获取应用路径
     */
    fun getAppPath(packageName: String = Utils.getApp().packageName): String {
        if (UtilsBridge.isSpace(packageName)) return ""
        return try {
            val pm = Utils.getApp().packageManager
            val pi = pm.getPackageInfo(packageName, 0)
            pi?.applicationInfo?.sourceDir ?: ""
        } catch (e: PackageManager.NameNotFoundException) {
            ""
        }
    }

    // ==================== 应用设置 ====================

    /**
     * 打开应用详情设置
     */
    fun openAppDetailsSettings(packageName: String = Utils.getApp().packageName) {
        if (UtilsBridge.isSpace(packageName)) return

        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        Utils.getApp().startActivity(intent)
    }

    /**
     * 打开应用详情设置（带回调）
     */
    fun openAppDetailsSettings(
        activity: Activity,
        requestCode: Int,
        packageName: String = Utils.getApp().packageName
    ) {
        if (UtilsBridge.isSpace(packageName)) return

        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", packageName, null)
        }
        activity.startActivityForResult(intent, requestCode)
    }

    // ==================== 应用签名 ====================

    /**
     * 获取应用签名
     */
    fun getAppSignatures(packageName: String = Utils.getApp().packageName): Array<Signature>? {
        if (UtilsBridge.isSpace(packageName)) return null
        return try {
            val pm = Utils.getApp().packageManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val pi = pm.getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES)
                val signingInfo = pi.signingInfo
                if (signingInfo?.hasMultipleSigners() == true) {
                    signingInfo.apkContentsSigners
                } else {
                    signingInfo?.signingCertificateHistory
                }
            } else {
                @Suppress("DEPRECATION")
                val pi = pm.getPackageInfo(packageName, PackageManager.GET_SIGNATURES)
                pi?.signatures
            }
        } catch (e: PackageManager.NameNotFoundException) {
            null
        }
    }

    /**
     * 获取应用签名SHA1值
     */
    fun getAppSignatureSHA1(packageName: String = Utils.getApp().packageName): String? {
        val signatures = getAppSignatures(packageName) ?: return null
        return signatures.firstOrNull()?.let { signature ->
            try {
                val md = MessageDigest.getInstance("SHA1")
                md.update(signature.toByteArray())
                UtilsBridge.bytes2HexString(md.digest())
            } catch (e: Exception) {
                null
            }
        }
    }

    // ==================== 应用信息数据类 ====================

    /**
     * 应用信息数据类
     */
    data class AppInfo(
        val packageName: String,
        val name: String,
        val icon: Drawable?,
        val versionName: String,
        val versionCode: Int,
        val isSystem: Boolean,
        val isDebug: Boolean
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

    /**
     * 获取应用信息
     */
    fun getAppInfo(packageName: String = Utils.getApp().packageName): AppInfo? {
        if (UtilsBridge.isSpace(packageName)) return null

        return try {
            val pm = Utils.getApp().packageManager
            val pi = pm.getPackageInfo(packageName, 0)
            pi.applicationInfo?.let { ai ->
                AppInfo(
                    packageName = packageName,
                    name = ai.loadLabel(pm).toString(),
                    icon = ai.loadIcon(pm),
                    versionName = pi.versionName ?: "",
                    versionCode = pi.versionCode,
                    isSystem = (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0,
                    isDebug = (ai.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
                )
            }
        } catch (e: PackageManager.NameNotFoundException) {
            null
        }
    }

    /**
     * 获取所有已安装应用信息
     */
    fun getAllAppInfo(): List<AppInfo> {
        return try {
            val pm = Utils.getApp().packageManager
            val installedPackages = pm.getInstalledPackages(0)

            installedPackages.mapNotNull { pi ->
                try {
                    pi.applicationInfo?.let { ai ->
                        AppInfo(
                            packageName = pi.packageName,
                            name = ai.loadLabel(pm).toString(),
                            icon = ai.loadIcon(pm),
                            versionName = pi.versionName ?: "",
                            versionCode = pi.versionCode,
                            isSystem = (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0,
                            isDebug = (ai.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
                        )
                    }
                } catch (e: Exception) {
                    null
                }
            }
        } catch (e: Exception) {
            emptyList()
        }
    }
}
