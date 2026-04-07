// DEPRECATED：可以删除，已被 Firebase crash report 替代
package com.ai.core.utils

import android.app.Application
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.lang.Thread.UncaughtExceptionHandler
import java.nio.file.FileSystems
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.collections.iterator

/** 崩溃工具类 提供崩溃处理相关的工具方法 */
object CrashUtils {

    private val FILE_SEP =
        try {
            FileSystems.getDefault().separator
        } catch (e: Exception) {
            "/" // 默认分隔符
        }

    private val DEFAULT_UNCAUGHT_EXCEPTION_HANDLER = Thread.getDefaultUncaughtExceptionHandler()

    /** 初始化 */
    fun init() {
        init("")
    }

    /**
     * 初始化
     *
     * @param crashDir 保存崩溃信息的目录
     */
    fun init(crashDir: File) {
        init(crashDir.absolutePath, null)
    }

    /**
     * 初始化
     *
     * @param crashDirPath 保存崩溃信息的目录路径
     */
    fun init(crashDirPath: String) {
        init(crashDirPath, null)
    }

    /**
     * 初始化
     *
     * @param onCrashListener 崩溃监听器
     */
    fun init(onCrashListener: OnCrashListener?) {
        init("", onCrashListener)
    }

    /**
     * 初始化
     *
     * @param crashDir 保存崩溃信息的目录
     * @param onCrashListener 崩溃监听器
     */
    fun init(crashDir: File, onCrashListener: OnCrashListener?) {
        init(crashDir.absolutePath, onCrashListener)
    }

    /**
     * 初始化
     *
     * @param crashDirPath 保存崩溃信息的目录路径
     * @param onCrashListener 崩溃监听器
     */
    fun init(crashDirPath: String, onCrashListener: OnCrashListener?) {
        val dirPath =
            if (UtilsBridge.isSpace(crashDirPath)) {
                try {
                    val app: Application? = Utils.getApp()
                    if (app != null) {
                        app.filesDir.toString() + FILE_SEP + "crash" + FILE_SEP
                    } else {
                        "/crash/"
                    }
                } catch (e: Exception) {
                    "/crash/"
                }
            } else {
                if (crashDirPath.endsWith(FILE_SEP)) crashDirPath else crashDirPath + FILE_SEP
            }

        Thread.setDefaultUncaughtExceptionHandler(
            getUncaughtExceptionHandler(dirPath, onCrashListener)
        )
    }

    private fun getUncaughtExceptionHandler(
        dirPath: String,
        onCrashListener: OnCrashListener?,
    ): UncaughtExceptionHandler {
        return UncaughtExceptionHandler { t, e ->
            val time = SimpleDateFormat("yyyy_MM_dd-HH_mm_ss", Locale.getDefault()).format(Date())
            val info = CrashInfo(time, e)
            val crashFile = "$dirPath$time.txt"
            // 简化实现，不实际写入文件

            DEFAULT_UNCAUGHT_EXCEPTION_HANDLER?.uncaughtException(t, e)
            onCrashListener?.onCrash(info)
        }
    }

    ///////////////////////////////////////////////////////////////////////////
    // interface
    ///////////////////////////////////////////////////////////////////////////

    interface OnCrashListener {
        fun onCrash(crashInfo: CrashInfo)
    }

    class CrashInfo(time: String, throwable: Throwable) {
        private val fileHeadProvider = FileHead("Crash")
        private val throwable: Throwable = throwable

        init {
            fileHeadProvider.addFirst("Time Of Crash", time)
        }

        fun addExtraHead(extraHead: Map<String, String>) {
            fileHeadProvider.append(extraHead)
        }

        fun addExtraHead(key: String, value: String) {
            fileHeadProvider.append(key, value)
        }

        fun getThrowable(): Throwable = throwable

        override fun toString(): String {
            return fileHeadProvider.toString() + getFullStackTrace(throwable)
        }
    }

    // 简化的FileHead类
    private class FileHead(head: String) {
        private val headInfo = kotlin.text.StringBuilder()

        init {
            headInfo.append("$head\n")
        }

        fun addFirst(key: String, value: String) {
            headInfo.insert(headInfo.indexOf("\n") + 1, "$key: $value\n")
        }

        fun append(key: String, value: String) {
            headInfo.append("$key: $value\n")
        }

        fun append(extraHead: Map<String, String>) {
            for ((key, value) in extraHead) {
                append(key, value)
            }
        }

        override fun toString(): String = headInfo.toString()
    }

    // 获取完整堆栈信息
    private fun getFullStackTrace(throwable: Throwable): String {
        val sw = StringWriter()
        val pw = PrintWriter(sw)
        throwable.printStackTrace(pw)
        return sw.toString()
    }
}
