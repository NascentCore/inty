package com.ai.core.utils

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.content.pm.Signature
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.Process
import android.provider.Settings
import android.util.Log
import androidx.core.content.pm.PackageInfoCompat
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.preferencesDataStore
import java.io.IOException
import kotlin.system.exitProcess
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking

private const val DEBUG_MODE_DATASTORE_NAME = "debug_mode_settings"
private const val KEY_DEBUG_MODE = "debug_mode"
private val Context.debugModeDataStore by preferencesDataStore(name = DEBUG_MODE_DATASTORE_NAME)

/** 应用工具类 提供应用相关的工具方法 */
object AppUtils {
    private const val TAG = "AppUtils"
    private const val BUILD_TYPE_DEBUG = "debug"
    private val DEBUG_MODE_PREF_KEY = booleanPreferencesKey(KEY_DEBUG_MODE)
    @Volatile private var cachedDebugModeOverride: Boolean? = null
    @Volatile private var debugModeOverrideLoaded: Boolean = false

    /**
     * Debug 模式状态流：
     * 1. 优先使用 DataStore 中的手动设置值
     * 2. 当未设置时回退到应用 BuildType 判断
     */
    fun debugModeFlow(context: Context = Utils.getApp()): Flow<Boolean> {
        val appContext = context.applicationContext
        val defaultValue = isBuildTypeDebug(appContext)
        return appContext.debugModeDataStore.data
            .catch { error ->
                if (error is IOException) {
                    Log.e(TAG, "读取 Debug Mode 失败，回退默认值", error)
                    emit(emptyPreferences())
                } else {
                    throw error
                }
            }
            .map { preferences ->
                val override = preferences[DEBUG_MODE_PREF_KEY]
                cachedDebugModeOverride = override
                debugModeOverrideLoaded = true
                override ?: defaultValue
            }
            .distinctUntilChanged()
    }

    /** 判断当前是否为 Debug 模式（优先读取 DataStore 手动开关） */
    fun isDebugMode(context: Context = Utils.getApp()): Boolean {
        val appContext = context.applicationContext
        if (debugModeOverrideLoaded) {
            return cachedDebugModeOverride ?: isBuildTypeDebug(appContext)
        }
        val override = runBlocking {
            appContext.debugModeDataStore.data
                .catch { error ->
                    if (error is IOException) {
                        Log.e(TAG, "读取 Debug Mode 失败，回退默认值", error)
                        emit(emptyPreferences())
                    } else {
                        throw error
                    }
                }
                .map { preferences -> preferences[DEBUG_MODE_PREF_KEY] }
                .first()
        }
        cachedDebugModeOverride = override
        debugModeOverrideLoaded = true
        return override ?: isBuildTypeDebug(appContext)
    }

    /** 手动设置 Debug 模式开关，并持久化到 DataStore */
    suspend fun setDebugMode(enabled: Boolean, context: Context = Utils.getApp()) {
        context.applicationContext.debugModeDataStore.edit { preferences ->
            preferences[DEBUG_MODE_PREF_KEY] = enabled
        }
        cachedDebugModeOverride = enabled
        debugModeOverrideLoaded = true
    }

    // ==================== 应用状态监听 ====================

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
            Handler(Looper.getMainLooper())
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
    fun getPackageName(): String = Utils.getApp().packageName ?: ""

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

    private fun PackageInfo.versionCodeCompat(): Int {
        val versionCode = PackageInfoCompat.getLongVersionCode(this)
        return versionCode.coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
    }

    private fun getLegacySignatures(pm: PackageManager, packageName: String): Array<Signature>? {
        @Suppress("DEPRECATION")
        val packageInfo = pm.getPackageInfo(packageName, PackageManager.GET_SIGNATURES)
        @Suppress("DEPRECATION")
        return packageInfo?.signatures
    }

    private fun isBuildTypeDebug(context: Context): Boolean {
        val appBuildType = readAppBuildType(context) ?: return false
        return appBuildType.equals(BUILD_TYPE_DEBUG, ignoreCase = true)
    }

    private fun readAppBuildType(context: Context): String? {
        val appBuildConfigClassName = "${context.packageName}.BuildConfig"
        return runCatching {
                val buildConfigClass = Class.forName(appBuildConfigClassName)
                buildConfigClass.getField("BUILD_TYPE").get(null) as? String
            }
            .getOrNull()
    }
}
