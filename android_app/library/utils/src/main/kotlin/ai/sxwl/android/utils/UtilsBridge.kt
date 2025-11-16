package ai.sxwl.android.utils

import android.annotation.SuppressLint
import android.app.Activity
import android.app.ActivityManager
import android.app.Application
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.ContextWrapper
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.util.Base64
import android.util.Log
import java.io.File
import java.io.FileWriter
import java.io.IOException
import java.lang.ref.WeakReference
import java.security.MessageDigest
import java.util.concurrent.ConcurrentHashMap
import kotlinx.serialization.json.Json

/** 工具类桥接器，提供各种工具类的核心功能 */
@SuppressLint("StaticFieldLeak")
internal object UtilsBridge {

    private var sApplication: Application? = null
    private val activityList = mutableListOf<Activity>()
    private var topActivity: Activity? = null
    private val jsonCache = ConcurrentHashMap<String, Json>()
    private val appStatusListeners = mutableListOf<Utils.OnAppStatusChangedListener>()

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
        appStatusListeners.clear()
    }

    fun getTopActivity(): Activity? = topActivity

    fun getActivityList(): List<Activity> = activityList.toList()

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

    /** 添加应用状态变化监听器 */
    fun addOnAppStatusChangedListener(listener: Utils.OnAppStatusChangedListener) {
        if (!appStatusListeners.contains(listener)) {
            appStatusListeners.add(listener)
        }
    }

    /** 移除应用状态变化监听器 */
    fun removeOnAppStatusChangedListener(listener: Utils.OnAppStatusChangedListener) {
        appStatusListeners.remove(listener)
    }

    /** 执行命令 */
    fun execCmd(command: String, isRoot: Boolean): ExecResult {
        return try {
            val process =
                if (isRoot) {
                    Runtime.getRuntime().exec("su")
                } else {
                    Runtime.getRuntime().exec(command)
                }

            if (isRoot) {
                val outputStream = process.outputStream
                outputStream.write(command.toByteArray())
                outputStream.write('\n'.code)
                outputStream.flush()
                outputStream.close()
            }

            val result = process.waitFor()
            val successMsg = process.inputStream.bufferedReader().readText()
            val errorMsg = process.errorStream.bufferedReader().readText()

            ExecResult(result, successMsg, errorMsg)
        } catch (e: Exception) {
            Log.e("UtilsBridge", "execCmd failed", e)
            ExecResult(-1, "", e.message ?: "")
        }
    }

    /** 判断应用是否在前台 */
    fun isAppForeground(): Boolean {
        val foregroundProcessName = getForegroundProcessName()
        return foregroundProcessName == sApplication?.packageName
    }

    /** 获取前台进程名称 */
    fun getForegroundProcessName(): String {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
                val usageStatsManager =
                    sApplication?.getSystemService(Context.USAGE_STATS_SERVICE)
                        as? UsageStatsManager
                if (usageStatsManager != null) {
                    val endTime = System.currentTimeMillis()
                    val beginTime = endTime - 1000 * 60 * 60 * 24 // 24小时前
                    val usageEvents = usageStatsManager.queryEvents(beginTime, endTime)
                    val event = UsageEvents.Event()
                    var lastPackageName = ""

                    while (usageEvents.hasNextEvent()) {
                        usageEvents.getNextEvent(event)
                        if (isMoveToForegroundEvent(event.eventType)) {
                            lastPackageName = event.packageName
                        }
                    }

                    lastPackageName
                } else {
                    ""
                }
            } else {
                // 对于低版本Android，使用ActivityManager
                val activityManager =
                    sApplication?.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
                @Suppress("DEPRECATION") val runningTasks = activityManager?.getRunningTasks(1)
                runningTasks?.firstOrNull()?.topActivity?.packageName ?: ""
            }
        } catch (e: Exception) {
            Log.e("UtilsBridge", "getForegroundProcessName failed", e)
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

    /** 命令执行结果 */
    data class ExecResult(val result: Int, val successMsg: String, val errorMsg: String)

    fun isActivityAlive(activity: Activity?): Boolean {
        return activity != null &&
            !activity.isFinishing &&
            (Build.VERSION.SDK_INT < Build.VERSION_CODES.JELLY_BEAN_MR1 || !activity.isDestroyed)
    }

    fun isSpace(str: String?): Boolean {
        return str.isNullOrBlank()
    }

    fun getActivityByContext(context: Context?): Activity? {
        if (context == null) return null
        var ctx = context
        val list = mutableListOf<Context>()
        while (ctx is ContextWrapper) {
            if (ctx is Activity) {
                return ctx
            }
            val activity = getActivityFromDecorContext(ctx)
            if (activity != null) return activity
            list.add(ctx)
            ctx = ctx.baseContext
            if (ctx == null) return null
            if (list.contains(ctx)) return null // loop context
        }
        return null
    }

    private fun getActivityFromDecorContext(context: Context?): Activity? {
        if (context == null) return null
        if (context.javaClass.name == "com.android.internal.policy.DecorContext") {
            try {
                val field = context.javaClass.getDeclaredField("mActivityContext")
                field.isAccessible = true
                val candidate = field.get(context)
                if (candidate is WeakReference<*>) {
                    val activity = candidate.get()
                    if (activity is Activity) {
                        return activity
                    }
                }
            } catch (e: Exception) {
                // ignore
            }
        }
        return null
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

    // Json相关方法
    fun getJson4LogUtils(): Json {
        return jsonCache.getOrPut("LogUtils") {
            Json {
                prettyPrint = true
                ignoreUnknownKeys = true
                encodeDefaults = true
            }
        }
    }

    private fun isMoveToForegroundEvent(eventType: Int): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            eventType == UsageEvents.Event.ACTIVITY_RESUMED
        } else {
            @Suppress("DEPRECATION")
            eventType == UsageEvents.Event.MOVE_TO_FOREGROUND
        }
    }

    // 存储卡相关方法
    fun isSDCardEnableByEnvironment(): Boolean {
        return Environment.getExternalStorageState() == Environment.MEDIA_MOUNTED
    }

    // 编码解码相关方法
    fun bytes2HexString(bytes: ByteArray?): String {
        if (bytes == null || bytes.isEmpty()) return ""
        val sb = StringBuilder()
        for (b in bytes) {
            val hex = Integer.toHexString(0xFF and b.toInt())
            if (hex.length == 1) {
                sb.append('0')
            }
            sb.append(hex)
        }
        return sb.toString()
    }

    fun hexString2Bytes(hexString: String?): ByteArray {
        if (hexString.isNullOrEmpty() || hexString.length % 2 != 0) return ByteArray(0)
        val len = hexString.length
        val data = ByteArray(len / 2)
        for (i in 0 until len step 2) {
            data[i / 2] =
                ((Character.digit(hexString[i], 16) shl 4) + Character.digit(hexString[i + 1], 16))
                    .toByte()
        }
        return data
    }

    fun base64Encode(input: ByteArray?): ByteArray? {
        return if (input == null || input.isEmpty()) null else Base64.encode(input, Base64.DEFAULT)
    }

    fun base64Decode(input: ByteArray?): ByteArray? {
        return if (input == null || input.isEmpty()) null else Base64.decode(input, Base64.DEFAULT)
    }

    fun base64Decode(input: String?): ByteArray? {
        return if (input.isNullOrEmpty()) null else Base64.decode(input, Base64.DEFAULT)
    }

    // 哈希加密模板方法
    fun hashTemplate(data: ByteArray?, algorithm: String): ByteArray? {
        if (data == null || data.isEmpty()) return null
        return try {
            val md = MessageDigest.getInstance(algorithm)
            md.update(data)
            md.digest()
        } catch (e: Exception) {
            Log.e("UtilsBridge", "hashTemplate failed", e)
            null
        }
    }

    /** 文件头部信息类 */
    class FileHead(private val name: String) {
        private val first = mutableMapOf<String, String>()
        private val last = mutableMapOf<String, String>()

        fun addFirst(key: String, value: String) {
            first[key] = value
        }

        fun append(extra: Map<String, String>) {
            last.putAll(extra)
        }

        fun append(key: String, value: String) {
            last[key] = value
        }

        fun getAppended(): String {
            return buildString {
                for ((key, value) in last) {
                    append(key).append(": ").append(value).append("\n")
                }
            }
        }

        override fun toString(): String {
            return buildString {
                val border = "************* $name Head ****************\n"
                append(border)
                for ((key, value) in first) {
                    append(key).append(": ").append(value).append("\n")
                }

                append("Rom Info           : ").append("Unknown").append("\n")
                append("Device Manufacturer: ").append(Build.MANUFACTURER).append("\n")
                append("Device Model       : ").append(Build.MODEL).append("\n")
                append("Android Version    : ").append(Build.VERSION.RELEASE).append("\n")
                append("Android SDK        : ").append(Build.VERSION.SDK_INT).append("\n")
                append("App VersionName    : ").append("Unknown").append("\n")
                append("App VersionCode    : ").append("0").append("\n")

                append(getAppended())
                append(border).append("\n")
            }
        }
    }
}
