package com.ai.core.utils

import android.annotation.SuppressLint
import android.os.Build
import android.provider.Settings
import java.io.File
import java.util.Locale
import java.util.TimeZone
import java.util.UUID

/** 设备工具类 提供设备信息相关的工具方法 */
object DeviceUtils {

    private val ROOT_LOCATIONS =
        arrayOf(
            "/system/bin/",
            "/system/xbin/",
            "/sbin/",
            "/system/sd/xbin/",
            "/system/bin/failsafe/",
            "/data/local/xbin/",
            "/data/local/bin/",
            "/data/local/",
            "/system/sbin/",
            "/usr/bin/",
            "/vendor/bin/",
        )

    /** 判断设备是否已root */
    fun isDeviceRooted(): Boolean {
        return ROOT_LOCATIONS.any { File("$it/su").exists() }
    }

    /** 获取设备系统版本名称 */
    fun getSDKVersionName(): String = Build.VERSION.RELEASE

    /** 获取设备系统版本号 */
    fun getSDKVersionCode(): Int = Build.VERSION.SDK_INT

    /** 获取设备Android ID */
    @SuppressLint("HardwareIds")
    fun getAndroidID(): String {
        return try {
            val app = Utils.getApp() ?: return ""
            val id = Settings.Secure.getString(app.contentResolver, Settings.Secure.ANDROID_ID)
            // 9774d56d682e549c 是 Android 模拟器的默认 Android ID，不是真实设备标识，应过滤掉
            if ("9774d56d682e549c" == id) "" else id ?: ""
        } catch (e: Exception) {
            ""
        }
    }

    /** 获取设备制造商 */
    fun getManufacturer(): String = Build.MANUFACTURER

    /** 获取设备型号 */
    fun getModel(): String = Build.MODEL.ifEmpty { "unknown" }

    /** 获取设备品牌 */
    fun getBrand(): String = Build.BRAND

    /** 获取设备产品名称 */
    fun getProduct(): String = Build.PRODUCT

    /** 获取设备序列号 */
    @SuppressLint("HardwareIds")
    fun getSerial(): String {
        return when {
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q -> getAndroidID()
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.O -> {
                try {
                    Build.getSerial()
                } catch (e: SecurityException) {
                    ""
                } catch (e: Exception) {
                    ""
                }
            }

            else -> {
                @Suppress("DEPRECATION") Build.SERIAL
            }
        }
    }

    /** 获取设备唯一标识符 */
    fun getUniqueDeviceId(): String {
        val androidId = getAndroidID()
        val serial = getSerial()
        val uuid = UUID.nameUUIDFromBytes("$androidId$serial".toByteArray()).toString()
        return uuid.replace("-", "")
    }

    /** 判断是否为模拟器 */
    fun isEmulator(): Boolean {
        return (Build.FINGERPRINT.startsWith("generic") ||
            Build.FINGERPRINT.startsWith("unknown") ||
            Build.MODEL.contains("google_sdk") ||
            Build.MODEL.contains("Emulator") ||
            Build.MODEL.contains("Android SDK built for x86") ||
            Build.MANUFACTURER.contains("Genymotion") ||
            (Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic")) ||
            "google_sdk" == Build.PRODUCT)
    }

    /** 获取设备屏幕宽度 */
    fun getScreenWidth(): Int {
        return try {
            val app = Utils.getApp() ?: return 0
            app.resources.displayMetrics.widthPixels
        } catch (e: Exception) {
            0
        }
    }

    /** 获取设备屏幕高度 */
    fun getScreenHeight(): Int {
        return try {
            val app = Utils.getApp() ?: return 0
            app.resources.displayMetrics.heightPixels
        } catch (e: Exception) {
            0
        }
    }

    /** 获取设备屏幕密度 */
    fun getScreenDensity(): Float {
        return try {
            val app = Utils.getApp() ?: return 1.0f
            app.resources.displayMetrics.density
        } catch (e: Exception) {
            1.0f
        }
    }

    /** 获取设备屏幕密度DPI */
    fun getScreenDensityDpi(): Int {
        return try {
            val app = Utils.getApp() ?: return 160
            app.resources.displayMetrics.densityDpi
        } catch (e: Exception) {
            160
        }
    }

    /** 获取设备时区ID（如 "Asia/Shanghai"） */
    fun getTimeZoneId(): String {
        return try {
            TimeZone.getDefault().id
        } catch (e: Exception) {
            "UTC"
        }
    }

    /** 获取设备当前语言代码（如 "zh", "en"） */
    fun getLanguageCode(): String {
        return try {
            Locale.getDefault().language
        } catch (e: Exception) {
            "en"
        }
    }

    /** 获取设备当前国家/地区代码（如 "CN", "US"） */
    fun getCountryCode(): String {
        return try {
            Locale.getDefault().country
        } catch (e: Exception) {
            ""
        }
    }
}
