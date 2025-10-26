package ai.sxwl.android.utils

import android.content.Context
import android.os.StatFs
import android.util.Log
import java.io.File

/** 存储工具类 提供存储相关的工具方法 */
object StoreUtils {

    /** 获取内部存储总大小 */
    fun getInternalStorageTotalSize(): Long {
        return try {
            getInternalStorageTotalSize(Utils.getApp())
        } catch (e: Exception) {
            Log.e("StoreUtils", "获取内部存储总大小失败", e)
            0L
        }
    }

    /** 获取内部存储总大小 */
    fun getInternalStorageTotalSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val filesDir = context.filesDir
            if (filesDir == null || !filesDir.exists()) {
                Log.w("StoreUtils", "filesDir不存在")
                return 0L
            }
            val statFs = StatFs(filesDir.absolutePath)
            val blockCount = statFs.blockCountLong
            val blockSize = statFs.blockSizeLong

            // 检查值是否合理
            if (blockCount < 0 || blockSize < 0) {
                Log.w("StoreUtils", "StatFs返回异常值: blockCount=$blockCount, blockSize=$blockSize")
                return 0L
            }

            return blockCount * blockSize
        } catch (e: SecurityException) {
            Log.e("StoreUtils", "权限不足，无法访问存储", e)
            return 0L
        } catch (e: Exception) {
            Log.e("StoreUtils", "获取内部存储总大小失败", e)
            return 0L
        }
    }

    /** 获取内部存储可用大小 */
    fun getInternalStorageAvailableSize(): Long {
        return try {
            getInternalStorageAvailableSize(Utils.getApp())
        } catch (e: Exception) {
            Log.e("StoreUtils", "获取内部存储可用大小失败", e)
            0L
        }
    }

    /** 获取内部存储可用大小 */
    fun getInternalStorageAvailableSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val filesDir = context.filesDir
            if (filesDir == null || !filesDir.exists()) {
                Log.w("StoreUtils", "filesDir不存在")
                return 0L
            }
            val statFs = StatFs(filesDir.absolutePath)
            val availableBlocks = statFs.availableBlocksLong
            val blockSize = statFs.blockSizeLong

            // 检查值是否合理
            if (availableBlocks < 0 || blockSize < 0) {
                Log.w(
                    "StoreUtils",
                    "StatFs返回异常值: availableBlocks=$availableBlocks, blockSize=$blockSize"
                )
                return 0L
            }

            return availableBlocks * blockSize
        } catch (e: SecurityException) {
            Log.e("StoreUtils", "权限不足，无法访问存储", e)
            return 0L
        } catch (e: Exception) {
            Log.e("StoreUtils", "获取内部存储可用大小失败", e)
            return 0L
        }
    }

    /** 获取内部存储已用大小 */
    fun getInternalStorageUsedSize(): Long {
        return getInternalStorageUsedSize(Utils.getApp())
    }

    /** 获取内部存储已用大小 */
    fun getInternalStorageUsedSize(context: Context?): Long {
        if (context == null) return 0L
        return getInternalStorageTotalSize(context) - getInternalStorageAvailableSize(context)
    }

    /** 获取内部存储总大小（格式化） */
    fun getInternalStorageTotalSizeFormat(): String {
        return getInternalStorageTotalSizeFormat(Utils.getApp())
    }

    /** 获取内部存储总大小（格式化） */
    fun getInternalStorageTotalSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getInternalStorageTotalSize(context))
    }

    /** 获取内部存储可用大小（格式化） */
    fun getInternalStorageAvailableSizeFormat(): String {
        return getInternalStorageAvailableSizeFormat(Utils.getApp())
    }

    /** 获取内部存储可用大小（格式化） */
    fun getInternalStorageAvailableSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getInternalStorageAvailableSize(context))
    }

    /** 获取内部存储已用大小（格式化） */
    fun getInternalStorageUsedSizeFormat(): String {
        return getInternalStorageUsedSizeFormat(Utils.getApp())
    }

    /** 获取内部存储已用大小（格式化） */
    fun getInternalStorageUsedSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getInternalStorageUsedSize(context))
    }

    /** 获取内部存储使用率 */
    fun getInternalStorageUsageRate(): Float {
        return getInternalStorageUsageRate(Utils.getApp())
    }

    /** 获取内部存储使用率 */
    fun getInternalStorageUsageRate(context: Context?): Float {
        if (context == null) return 0f
        val totalSize = getInternalStorageTotalSize(context)
        if (totalSize == 0L) return 0f
        return getInternalStorageUsedSize(context).toFloat() / totalSize.toFloat() * 100f
    }

    /** 获取应用数据大小 */
    fun getAppDataSize(): Long {
        return getAppDataSize(Utils.getApp())
    }

    /** 获取应用数据大小 */
    fun getAppDataSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val dataDir = File(context.applicationInfo.dataDir)
            return getDirSize(dataDir)
        } catch (e: Exception) {
            e.printStackTrace()
            return 0L
        }
    }

    /** 获取应用数据大小（格式化） */
    fun getAppDataSizeFormat(): String {
        return getAppDataSizeFormat(Utils.getApp())
    }

    /** 获取应用数据大小（格式化） */
    fun getAppDataSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getAppDataSize(context))
    }

    /** 获取应用缓存大小 */
    fun getAppCacheSize(): Long {
        return getAppCacheSize(Utils.getApp())
    }

    /** 获取应用缓存大小 */
    fun getAppCacheSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val cacheDir = context.cacheDir
            return getDirSize(cacheDir)
        } catch (e: Exception) {
            e.printStackTrace()
            return 0L
        }
    }

    /** 获取应用缓存大小（格式化） */
    fun getAppCacheSizeFormat(): String {
        return getAppCacheSizeFormat(Utils.getApp())
    }

    /** 获取应用缓存大小（格式化） */
    fun getAppCacheSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getAppCacheSize(context))
    }

    /** 获取应用文件大小 */
    fun getAppFilesSize(): Long {
        return getAppFilesSize(Utils.getApp())
    }

    /** 获取应用文件大小 */
    fun getAppFilesSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val filesDir = context.filesDir
            return getDirSize(filesDir)
        } catch (e: Exception) {
            e.printStackTrace()
            return 0L
        }
    }

    /** 获取应用文件大小（格式化） */
    fun getAppFilesSizeFormat(): String {
        return getAppFilesSizeFormat(Utils.getApp())
    }

    /** 获取应用文件大小（格式化） */
    fun getAppFilesSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getAppFilesSize(context))
    }

    /** 获取应用数据库大小 */
    fun getAppDatabaseSize(): Long {
        return getAppDatabaseSize(Utils.getApp())
    }

    /** 获取应用数据库大小 */
    fun getAppDatabaseSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val databaseDir = File(context.applicationInfo.dataDir, "databases")
            return getDirSize(databaseDir)
        } catch (e: Exception) {
            e.printStackTrace()
            return 0L
        }
    }

    /** 获取应用数据库大小（格式化） */
    fun getAppDatabaseSizeFormat(): String {
        return getAppDatabaseSizeFormat(Utils.getApp())
    }

    /** 获取应用数据库大小（格式化） */
    fun getAppDatabaseSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getAppDatabaseSize(context))
    }

    /** 获取应用SharedPreferences大小 */
    fun getAppSharedPreferencesSize(): Long {
        return getAppSharedPreferencesSize(Utils.getApp())
    }

    /** 获取应用SharedPreferences大小 */
    fun getAppSharedPreferencesSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val sharedPrefsDir = File(context.applicationInfo.dataDir, "shared_prefs")
            return getDirSize(sharedPrefsDir)
        } catch (e: Exception) {
            e.printStackTrace()
            return 0L
        }
    }

    /** 获取应用SharedPreferences大小（格式化） */
    fun getAppSharedPreferencesSizeFormat(): String {
        return getAppSharedPreferencesSizeFormat(Utils.getApp())
    }

    /** 获取应用SharedPreferences大小（格式化） */
    fun getAppSharedPreferencesSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getAppSharedPreferencesSize(context))
    }

    /** 获取应用外部缓存大小 */
    fun getAppExternalCacheSize(): Long {
        return getAppExternalCacheSize(Utils.getApp())
    }

    /** 获取应用外部缓存大小 */
    fun getAppExternalCacheSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val externalCacheDir = context.externalCacheDir
            if (externalCacheDir != null) {
                return getDirSize(externalCacheDir)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return 0L
    }

    /** 获取应用外部缓存大小（格式化） */
    fun getAppExternalCacheSizeFormat(): String {
        return getAppExternalCacheSizeFormat(Utils.getApp())
    }

    /** 获取应用外部缓存大小（格式化） */
    fun getAppExternalCacheSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getAppExternalCacheSize(context))
    }

    /** 获取应用外部文件大小 */
    fun getAppExternalFilesSize(): Long {
        return getAppExternalFilesSize(Utils.getApp())
    }

    /** 获取应用外部文件大小 */
    fun getAppExternalFilesSize(context: Context?): Long {
        if (context == null) return 0L
        try {
            val externalFilesDir = context.getExternalFilesDir(null)
            if (externalFilesDir != null) {
                return getDirSize(externalFilesDir)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return 0L
    }

    /** 获取应用外部文件大小（格式化） */
    fun getAppExternalFilesSizeFormat(): String {
        return getAppExternalFilesSizeFormat(Utils.getApp())
    }

    /** 获取应用外部文件大小（格式化） */
    fun getAppExternalFilesSizeFormat(context: Context?): String {
        return FileUtils.formatFileSize(getAppExternalFilesSize(context))
    }

    /** 检查内部存储空间是否足够 */
    fun isInternalStorageSpaceEnough(requiredSize: Long): Boolean {
        return isInternalStorageSpaceEnough(Utils.getApp(), requiredSize)
    }

    /** 检查内部存储空间是否足够 */
    fun isInternalStorageSpaceEnough(context: Context?, requiredSize: Long): Boolean {
        if (context == null) return false
        return getInternalStorageAvailableSize(context) >= requiredSize
    }

    /** 获取内部存储空间不足的提示信息 */
    fun getInternalStorageSpaceInsufficientMessage(requiredSize: Long): String {
        return getInternalStorageSpaceInsufficientMessage(Utils.getApp(), requiredSize)
    }

    /** 获取内部存储空间不足的提示信息 */
    fun getInternalStorageSpaceInsufficientMessage(context: Context?, requiredSize: Long): String {
        if (isInternalStorageSpaceEnough(context, requiredSize)) {
            return "内部存储空间充足"
        }
        val availableSize = getInternalStorageAvailableSize(context)
        val requiredSizeFormat = FileUtils.formatFileSize(requiredSize)
        val availableSizeFormat = FileUtils.formatFileSize(availableSize)
        return "内部存储空间不足，需要$requiredSizeFormat，可用$availableSizeFormat"
    }

    /** 获取目录大小 */
    private fun getDirSize(dir: File): Long {
        if (!dir.exists() || !dir.isDirectory) return 0L

        var size = 0L
        try {
            val files = dir.listFiles()
            if (files != null) {
                for (file in files) {
                    try {
                        size +=
                            if (file.isDirectory) {
                                getDirSize(file)
                            } else {
                                file.length()
                            }
                    } catch (e: SecurityException) {
                        Log.w("StoreUtils", "无法访问文件: ${file.absolutePath}", e)
                        // 继续处理其他文件，不中断整个流程
                    } catch (e: Exception) {
                        Log.w("StoreUtils", "处理文件失败: ${file.absolutePath}", e)
                        // 继续处理其他文件，不中断整个流程
                    }
                }
            }
        } catch (e: SecurityException) {
            Log.e("StoreUtils", "权限不足，无法访问目录: ${dir.absolutePath}", e)
            return 0L
        } catch (e: Exception) {
            Log.e("StoreUtils", "获取目录大小失败: ${dir.absolutePath}", e)
            return 0L
        }
        return size
    }

    /** 获取存储信息 */
    fun getStorageInfo(): Map<String, String> {
        return getStorageInfo(Utils.getApp())
    }

    /** 获取存储信息 */
    fun getStorageInfo(context: Context?): Map<String, String> {
        if (context == null) return emptyMap()

        val info = mutableMapOf<String, String>()
        info["internal_total"] = getInternalStorageTotalSizeFormat(context)
        info["internal_available"] = getInternalStorageAvailableSizeFormat(context)
        info["internal_used"] = getInternalStorageUsedSizeFormat(context)
        info["internal_usage_rate"] = String.format("%.2f%%", getInternalStorageUsageRate(context))
        info["app_data"] = getAppDataSizeFormat(context)
        info["app_cache"] = getAppCacheSizeFormat(context)
        info["app_files"] = getAppFilesSizeFormat(context)
        info["app_database"] = getAppDatabaseSizeFormat(context)
        info["app_shared_prefs"] = getAppSharedPreferencesSizeFormat(context)
        info["app_external_cache"] = getAppExternalCacheSizeFormat(context)
        info["app_external_files"] = getAppExternalFilesSizeFormat(context)

        return info
    }
}
