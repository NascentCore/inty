package ai.sxwl.android.utils

import android.app.Application
import android.content.Context
import android.os.Environment

/**
 * 路径工具类
 * 提供路径相关的工具方法
 */
object PathUtils {

    /**
     * 获取内部存储路径
     */
    fun getInternalAppFilesPath(): String {
        return try {
            val app: Application? = Utils.getApp()
            if (app != null) {
                app.filesDir.absolutePath
            } else {
                ""
            }
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * 获取内部存储路径
     */
    fun getInternalAppFilesPath(context: Context?): String {
        return context?.filesDir?.absolutePath ?: ""
    }

    /**
     * 获取内部服务器路径
     */
    fun getInternalAppCachePath(): String {
        return try {
            val app: Application? = Utils.getApp()
            if (app != null) {
                app.cacheDir.absolutePath
            } else {
                ""
            }
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * 获取内部服务器路径
     */
    fun getInternalAppCachePath(context: Context?): String {
        return context?.cacheDir?.absolutePath ?: ""
    }

    /**
     * 获取外部存储路径
     */
    fun getExternalStoragePath(): String {
        return try {
            val externalDir = Environment.getExternalStorageDirectory()
            if (externalDir != null) {
                externalDir.absolutePath
            } else {
                ""
            }
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * 获取外部存储路径
     */
    fun getExternalStoragePath(context: Context?): String {
        return try {
            val externalDir = Environment.getExternalStorageDirectory()
            if (externalDir != null) {
                externalDir.absolutePath
            } else {
                ""
            }
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * 获取外部应用文件路径
     */
    fun getExternalAppFilesPath(): String {
        return Utils.getApp().getExternalFilesDir(null)?.absolutePath ?: ""
    }

    /**
     * 获取外部应用文件路径
     */
    fun getExternalAppFilesPath(context: Context?): String {
        return context?.getExternalFilesDir(null)?.absolutePath ?: ""
    }

    /**
     * 获取外部应用服务器路径
     */
    fun getExternalAppCachePath(): String {
        return Utils.getApp().externalCacheDir?.absolutePath ?: ""
    }

    /**
     * 获取外部应用服务器路径
     */
    fun getExternalAppCachePath(context: Context?): String {
        return context?.externalCacheDir?.absolutePath ?: ""
    }

    /**
     * 获取外部应用文件路径（指定类型）
     */
    fun getExternalAppFilesPath(type: String?): String {
        return Utils.getApp().getExternalFilesDir(type)?.absolutePath ?: ""
    }

    /**
     * 获取外部应用文件路径（指定类型）
     */
    fun getExternalAppFilesPath(context: Context?, type: String?): String {
        return context?.getExternalFilesDir(type)?.absolutePath ?: ""
    }

    /**
     * 获取外部音乐路径
     */
    fun getExternalMusicPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC).absolutePath
    }

    /**
     * 获取外部播客路径
     */
    fun getExternalPodcastsPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PODCASTS).absolutePath
    }

    /**
     * 获取外部响路径
     */
    fun getExternalRingtonesPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_RINGTONES).absolutePath
    }

    /**
     * 获取外部闹钟路径
     */
    fun getExternalAlarmsPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_ALARMS).absolutePath
    }

    /**
     * 获取外部通知路径
     */
    fun getExternalNotificationsPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_NOTIFICATIONS).absolutePath
    }

    /**
     * 获取外部图片路径
     */
    fun getExternalPicturesPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES).absolutePath
    }

    /**
     * 获取外部电影路径
     */
    fun getExternalMoviesPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES).absolutePath
    }

    /**
     * 获取外部下载路径
     */
    fun getExternalDownloadsPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).absolutePath
    }

    /**
     * 获取外部文档路径
     */
    fun getExternalDocumentsPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS).absolutePath
    }

    /**
     * 获取外部DCIM路径
     */
    fun getExternalDcimPath(): String {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM).absolutePath
    }

    /**
     * 获取外部公共路径
     */
    fun getExternalPublicPath(type: String?): String {
        return Environment.getExternalStoragePublicDirectory(type).absolutePath
    }

    /**
     * 获取根路径
     */
    fun getRootPath(): String {
        return Environment.getRootDirectory().absolutePath
    }

    /**
     * 获取数据路径
     */
    fun getDataPath(): String {
        return Environment.getDataDirectory().absolutePath
    }

    /**
     * 获取下载存储路径
     */
    fun getDownloadCachePath(): String {
        return Environment.getDownloadCacheDirectory().absolutePath
    }

    /**
     * 获取应用数据路径
     */
    fun getAppDataPath(): String {
        return Utils.getApp().applicationInfo.dataDir
    }

    /**
     * 获取应用数据路径
     */
    fun getAppDataPath(context: Context?): String {
        return context?.applicationInfo?.dataDir ?: ""
    }

    /**
     * 获取应用代码路径
     */
    fun getAppCodePath(): String {
        return Utils.getApp().applicationInfo.sourceDir
    }

    /**
     * 获取应用代码路径
     */
    fun getAppCodePath(context: Context?): String {
        return context?.applicationInfo?.sourceDir ?: ""
    }

    /**
     * 获取应用资源路径
     */
    fun getAppResourcePath(): String {
        return Utils.getApp().applicationInfo.sourceDir
    }

    /**
     * 获取应用资源路径
     */
    fun getAppResourcePath(context: Context?): String {
        return context?.applicationInfo?.sourceDir ?: ""
    }

    /**
     * 获取应用数据库路径
     */
    fun getAppDbPath(): String {
        return Utils.getApp().getDatabasePath("").absolutePath
    }

    /**
     * 获取应用数据库路径
     */
    fun getAppDbPath(context: Context?): String {
        return context?.getDatabasePath("")?.absolutePath ?: ""
    }

    /**
     * 获取应用数据库路径（指定名称）
     */
    fun getAppDbPath(name: String?): String {
        return Utils.getApp().getDatabasePath(name).absolutePath
    }

    /**
     * 获取应用数据库路径（指定名称）
     */
    fun getAppDbPath(context: Context?, name: String?): String {
        return context?.getDatabasePath(name)?.absolutePath ?: ""
    }

    /**
     * 获取应用共享偏好设置路径
     */
    fun getAppSpPath(): String {
        return Utils.getApp().applicationInfo.dataDir + "/shared_prefs"
    }

    /**
     * 获取应用共享偏好设置路径
     */
    fun getAppSpPath(context: Context?): String {
        return context?.applicationInfo?.dataDir?.let { "$it/shared_prefs" } ?: ""
    }

    /**
     * 获取应用库路径
     */
    fun getAppLibPath(): String {
        return Utils.getApp().applicationInfo.nativeLibraryDir
    }

    /**
     * 获取应用库路径
     */
    fun getAppLibPath(context: Context?): String {
        return context?.applicationInfo?.nativeLibraryDir ?: ""
    }

    /**
     * 获取应用服务器路径
     */
    fun getAppCachePath(): String {
        return Utils.getApp().cacheDir.absolutePath
    }

    /**
     * 获取应用服务器路径
     */
    fun getAppCachePath(context: Context?): String {
        return context?.cacheDir?.absolutePath ?: ""
    }

    /**
     * 获取应用文件路径
     */
    fun getAppFilesPath(): String {
        return Utils.getApp().filesDir.absolutePath
    }

    /**
     * 获取应用文件路径
     */
    fun getAppFilesPath(context: Context?): String {
        return context?.filesDir?.absolutePath ?: ""
    }

    /**
     * 获取应用文件路径（指定名称）
     */
    fun getAppFilesPath(name: String?): String {
        return Utils.getApp().getDir(name, Context.MODE_PRIVATE).absolutePath
    }

    /**
     * 获取应用文件路径（指定名称）
     */
    fun getAppFilesPath(context: Context?, name: String?): String {
        return context?.getDir(name, Context.MODE_PRIVATE)?.absolutePath ?: ""
    }
}
