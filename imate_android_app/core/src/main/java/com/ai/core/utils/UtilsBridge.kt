package com.ai.core.utils

import android.annotation.SuppressLint
import android.app.Activity
import android.app.Application
import android.os.Bundle
import android.os.Environment
import android.util.Log
import java.io.File
import java.io.FileWriter
import java.io.IOException

/** 工具类桥接器，提供各种工具类的核心功能 */
@SuppressLint("StaticFieldLeak")
internal object UtilsBridge {

    private var sApplication: Application? = null
    private val activityList = mutableListOf<Activity>()
    private var topActivity: Activity? = null

    fun init(app: Application) {
        sApplication = app
        app.registerActivityLifecycleCallbacks(
            object : Application.ActivityLifecycleCallbacks {
                override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {
                    activityList.add(activity)
                    topActivity = activity
                }

                override fun onActivityStarted(activity: Activity) {
                    topActivity = activity
                }

                override fun onActivityResumed(activity: Activity) {
                    topActivity = activity
                }

                override fun onActivityPaused(activity: Activity) {}

                override fun onActivityStopped(activity: Activity) {}

                override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}

                override fun onActivityDestroyed(activity: Activity) {
                    activityList.remove(activity)
                    if (topActivity == activity) {
                        // 安全的获取最后一个Activity
                        topActivity = activityList.lastOrNull()
                    }
                }
            }
        )
    }

    fun unInit(app: Application) {
        sApplication = null
        activityList.clear()
        topActivity = null
    }

    @SuppressLint("PrivateApi")
    fun getApplicationByReflect(): Application? {
        return try {
            val activityThreadClass = Class.forName("android.app.ActivityThread")
            val thread = activityThreadClass.getMethod("currentActivityThread").invoke(null)
            val app = activityThreadClass.getMethod("getApplication").invoke(thread)
            app as? Application
        } catch (e: ClassNotFoundException) {
            Log.e("UtilsBridge", "ActivityThread class not found", e)
            null
        } catch (e: NoSuchMethodException) {
            Log.e("UtilsBridge", "Method not found", e)
            null
        } catch (e: Exception) {
            Log.e("UtilsBridge", "getApplicationByReflect failed", e)
            null
        }
    }

    @SuppressLint("PrivateApi")
    fun getCurrentProcessName(): String {
        return try {
            val activityThreadClass = Class.forName("android.app.ActivityThread")
            val thread = activityThreadClass.getMethod("currentActivityThread").invoke(null)
            val processName = activityThreadClass.getMethod("getProcessName").invoke(thread)
            processName as? String ?: ""
        } catch (e: ClassNotFoundException) {
            Log.e("UtilsBridge", "ActivityThread class not found", e)
            ""
        } catch (e: NoSuchMethodException) {
            Log.e("UtilsBridge", "Method not found", e)
            ""
        } catch (e: Exception) {
            Log.e("UtilsBridge", "getCurrentProcessName failed", e)
            ""
        }
    }

    /** 结束所有Activity */
    fun finishAllActivities() {
        activityList.forEach { activity ->
            if (!activity.isFinishing) {
                activity.finish()
            }
        }
        activityList.clear()
    }

    fun isSpace(str: String?): Boolean {
        return str.isNullOrBlank()
    }

    // 文件操作相关方法
    fun createOrExistsDir(dir: File?): Boolean {
        return dir?.let { if (it.exists()) it.isDirectory else it.mkdirs() } ?: false
    }

    fun writeFileFromString(filePath: String, content: String, append: Boolean): Boolean {
        return try {
            val file = File(filePath)
            if (!file.exists()) {
                val parentFile = file.parentFile
                if (parentFile != null && !parentFile.exists()) {
                    if (!parentFile.mkdirs()) return false
                }
                if (!file.createNewFile()) return false
            }
            FileWriter(file, append).use { writer -> writer.write(content) }
            true
        } catch (e: IOException) {
            Log.e("UtilsBridge", "writeFileFromString failed", e)
            false
        }
    }

    // 异常处理相关方法
    fun getFullStackTrace(throwable: Throwable): String {
        return buildString {
            append(throwable.toString()).append('\n')
            throwable.stackTrace.forEach { element ->
                append("\tat ").append(element.toString()).append('\n')
            }
            throwable.cause?.let { cause -> append("Caused by: ").append(getFullStackTrace(cause)) }
        }
    }

    // 存储卡相关方法
    fun isSDCardEnableByEnvironment(): Boolean {
        return Environment.getExternalStorageState() == Environment.MEDIA_MOUNTED
    }
}
