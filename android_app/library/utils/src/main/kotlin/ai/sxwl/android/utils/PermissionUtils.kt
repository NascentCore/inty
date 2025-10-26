package ai.sxwl.android.utils

import android.Manifest
import android.app.Activity
import android.app.Application
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

/**
 * 权限工具类
 * 提供权限相关的工具方法
 */
object PermissionUtils {

    /**
     * 查询权限是否已授予
     */
    fun isGranted(permission: String?): Boolean {
        return try {
            val app: Application? = Utils.getApp()
            if (app != null) {
                isGranted(app, permission)
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 查询权限是否已授予
     */
    fun isGranted(context: Context?, permission: String?): Boolean {
        if (context == null || permission.isNullOrEmpty()) return false
        return try {
            ContextCompat.checkSelfPermission(
                context,
                permission
            ) == PackageManager.PERMISSION_GRANTED
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 查询多个权限是否已授予
     */
    fun isGranted(vararg permissions: String?): Boolean {
        return isGranted(Utils.getApp(), *permissions)
    }

    /**
     * 查询多个权限是否已授予
     */
    fun isGranted(context: Context?, vararg permissions: String?): Boolean {
        if (context == null) return false
        for (permission in permissions) {
            if (!isGranted(context, permission)) {
                return false
            }
        }
        return true
    }

    /**
     * 检查权限是否应显示说明
     */
    fun shouldShowRequestPermissionRationale(permission: String?): Boolean {
        return try {
            val app: Application? = Utils.getApp()
            if (app != null) {
                shouldShowRequestPermissionRationale(app, permission)
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 检查权限是否应显示说明
     */
    fun shouldShowRequestPermissionRationale(context: Context?, permission: String?): Boolean {
        if (context == null || permission.isNullOrEmpty()) return false
        return try {
            ActivityCompat.shouldShowRequestPermissionRationale(
                context as Activity,
                permission
            )
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * 检查是否为永久拒绝的权限
     */
    fun isPermanentlyDenied(permission: String?): Boolean {
        return isPermanentlyDenied(Utils.getApp(), permission)
    }

    /**
     * 检查是否为永久拒绝的权限
     */
    fun isPermanentlyDenied(context: Context?, permission: String?): Boolean {
        if (context == null || permission.isNullOrEmpty()) return false
        return !isGranted(context, permission) && !shouldShowRequestPermissionRationale(
            context,
            permission
        )
    }

    /**
     * 获取未拥有的权限列表
     */
    fun getDeniedPermissions(vararg permissions: String?): List<String> {
        return getDeniedPermissions(Utils.getApp(), *permissions)
    }

    /**
     * 获取未拥有的权限列表
     */
    fun getDeniedPermissions(context: Context?, vararg permissions: String?): List<String> {
        if (context == null) return emptyList()
        val deniedPermissions = mutableListOf<String>()
        for (permission in permissions) {
            if (!isGranted(context, permission)) {
                permission?.let { deniedPermissions.add(it) }
            }
        }
        return deniedPermissions
    }

    /**
     * 获取已拥有的权限列表
     */
    fun getGrantedPermissions(vararg permissions: String?): List<String> {
        return getGrantedPermissions(Utils.getApp(), *permissions)
    }

    /**
     * 获取已拥有的权限列表
     */
    fun getGrantedPermissions(context: Context?, vararg permissions: String?): List<String> {
        if (context == null) return emptyList()
        val grantedPermissions = mutableListOf<String>()
        for (permission in permissions) {
            if (isGranted(context, permission)) {
                permission?.let { grantedPermissions.add(it) }
            }
        }
        return grantedPermissions
    }

    /**
     * 查看照片权限
     */
    fun hasCameraPermission(): Boolean {
        return isGranted(Manifest.permission.CAMERA)
    }

    /**
     * 查看照片权限
     */
    fun hasCameraPermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.CAMERA)
    }

    /**
     * 检查存储权限
     */
    fun hasStoragePermission(): Boolean {
        return isGranted(
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE
        )
    }

    /**
     * 检查存储权限
     */
    fun hasStoragePermission(context: Context?): Boolean {
        return isGranted(
            context,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE
        )
    }

    /**
     *查看位置权限
     */
    fun hasLocationPermission(): Boolean {
        return isGranted(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
    }

    /**
     *查看位置权限
     */
    fun hasLocationPermission(context: Context?): Boolean {
        return isGranted(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
    }

    /**
     *查询电话权限
     */
    fun hasPhonePermission(): Boolean {
        return isGranted(Manifest.permission.READ_PHONE_STATE, Manifest.permission.CALL_PHONE)
    }

    /**
     *查询电话权限
     */
    fun hasPhonePermission(context: Context?): Boolean {
        return isGranted(
            context,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.CALL_PHONE
        )
    }

    /**
     *查询短信权限
     */
    fun hasSmsPermission(): Boolean {
        return isGranted(Manifest.permission.SEND_SMS, Manifest.permission.READ_SMS)
    }

    /**
     *查询短信权限
     */
    fun hasSmsPermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.SEND_SMS, Manifest.permission.READ_SMS)
    }

    /**
     *查询麦克风权限
     */
    fun hasMicrophonePermission(): Boolean {
        return isGranted(Manifest.permission.RECORD_AUDIO)
    }

    /**
     *查询麦克风权限
     */
    fun hasMicrophonePermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.RECORD_AUDIO)
    }

    /**
     *查询干燥机权限
     */
    fun hasContactsPermission(): Boolean {
        return isGranted(Manifest.permission.READ_CONTACTS, Manifest.permission.WRITE_CONTACTS)
    }

    /**
     *查询干燥机权限
     */
    fun hasContactsPermission(context: Context?): Boolean {
        return isGranted(
            context,
            Manifest.permission.READ_CONTACTS,
            Manifest.permission.WRITE_CONTACTS
        )
    }

    /**
     *查看日历权限
     */
    fun hasCalendarPermission(): Boolean {
        return isGranted(Manifest.permission.READ_CALENDAR, Manifest.permission.WRITE_CALENDAR)
    }

    /**
     *查看日历权限
     */
    fun hasCalendarPermission(context: Context?): Boolean {
        return isGranted(
            context,
            Manifest.permission.READ_CALENDAR,
            Manifest.permission.WRITE_CALENDAR
        )
    }

    /**
     * 检查传感器权限
     */
    fun hasSensorPermission(): Boolean {
        return isGranted(Manifest.permission.BODY_SENSORS)
    }

    /**
     * 检查传感器权限
     */
    fun hasSensorPermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.BODY_SENSORS)
    }

    /**
     * 查看网络状态权限
     */
    fun hasNetworkStatePermission(): Boolean {
        return isGranted(Manifest.permission.ACCESS_NETWORK_STATE)
    }

    /**
     * 查看网络状态权限
     */
    fun hasNetworkStatePermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.ACCESS_NETWORK_STATE)
    }

    /**
     *查询WiFi状态权限
     */
    fun hasWifiStatePermission(): Boolean {
        return isGranted(Manifest.permission.ACCESS_WIFI_STATE)
    }

    /**
     *查询WiFi状态权限
     */
    fun hasWifiStatePermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.ACCESS_WIFI_STATE)
    }

    /**
     *查询蓝牙权限
     */
    fun hasBluetoothPermission(): Boolean {
        return isGranted(Manifest.permission.BLUETOOTH, Manifest.permission.BLUETOOTH_ADMIN)
    }

    /**
     *查询蓝牙权限
     */
    fun hasBluetoothPermission(context: Context?): Boolean {
        return isGranted(
            context,
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN
        )
    }

    /**
     *查询通知权限
     */
    fun hasNotificationPermission(): Boolean {
        return isGranted(Manifest.permission.POST_NOTIFICATIONS)
    }

    /**
     *查询通知权限
     */
    fun hasNotificationPermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.POST_NOTIFICATIONS)
    }
}
