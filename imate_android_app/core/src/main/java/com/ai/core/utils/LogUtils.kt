package com.ai.core.utils

import android.content.ClipData
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.annotation.IntDef
import androidx.annotation.RequiresApi
import androidx.collection.SimpleArrayMap
import java.io.File
import java.io.IOException
import java.io.StringReader
import java.io.StringWriter
import java.lang.reflect.ParameterizedType
import java.nio.file.FileSystems
import java.text.ParseException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.regex.Pattern
import javax.xml.transform.OutputKeys
import javax.xml.transform.Source
import javax.xml.transform.TransformerFactory
import javax.xml.transform.stream.StreamResult
import javax.xml.transform.stream.StreamSource
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import kotlin.collections.iterator

/** 日志工具类 提供完整的日志功能，支持控制台输出、文件输出、JSON格式化、XML格式化等 */
object LogUtils {
    const val V = Log.VERBOSE
    const val D = Log.DEBUG
    const val I = Log.INFO
    const val W = Log.WARN
    const val E = Log.ERROR
    const val A = Log.ASSERT

    @IntDef(V, D, I, W, E, A) @Retention(AnnotationRetention.SOURCE) annotation class TYPE

    private val T = charArrayOf('V', 'D', 'I', 'W', 'E', 'A')

    private const val FILE = 0x10
    private const val JSON = 0x20
    private const val XML = 0x30

    private val FILE_SEP = FileSystems.getDefault().separator
    private val LINE_SEP = System.lineSeparator()
    private const val TOP_CORNER = "┌"
    private const val MIDDLE_CORNER = "├"
    private const val LEFT_BORDER = "│ "
    private const val BOTTOM_CORNER = "└"
    private const val SIDE_DIVIDER = "────────────────────────────────────────────────────────"
    private const val MIDDLE_DIVIDER = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    private val TOP_BORDER = TOP_CORNER + SIDE_DIVIDER + SIDE_DIVIDER
    private val MIDDLE_BORDER = MIDDLE_CORNER + MIDDLE_DIVIDER + MIDDLE_DIVIDER
    private val BOTTOM_BORDER = BOTTOM_CORNER + SIDE_DIVIDER + SIDE_DIVIDER
    private const val MAX_LEN = 1100 // 适合中文字符
    private const val NOTHING = "log nothing"
    private const val NULL = "null"
    private const val ARGS = "args"
    private const val PLACEHOLDER = " "

    private val CONFIG = Config()
    private val EXECUTOR: ExecutorService = Executors.newSingleThreadExecutor()
    private val I_FORMATTER_MAP = SimpleArrayMap<Class<*>, IFormatter<*>>()

    // 使用 ThreadLocal 确保 SimpleDateFormat 的线程安全
    private val simpleDateFormat =
        ThreadLocal.withInitial {
            SimpleDateFormat("yyyy_MM_dd HH:mm:ss.SSS ", Locale.getDefault())
        }

    // 专门用于日期解析的 ThreadLocal SimpleDateFormat
    private val dateFormat =
        ThreadLocal.withInitial { SimpleDateFormat("yyyy_MM_dd", Locale.getDefault()) }

    fun getConfig(): Config = CONFIG

    // 基础日志方法
    fun v(vararg contents: Any?) = log(V, CONFIG.globalTag, *contents)

    fun d(vararg contents: Any?) = log(D, CONFIG.globalTag, *contents)

    fun i(vararg contents: Any?) = log(I, CONFIG.globalTag, *contents)

    fun w(vararg contents: Any?) = log(W, CONFIG.globalTag, *contents)

    fun e(vararg contents: Any?) = log(E, CONFIG.globalTag, *contents)

    fun log(type: Int, tag: String, vararg contents: Any?) {
        if (!CONFIG.logSwitch) return

        val typeLow = type and 0x0f
        val typeHigh = type and 0xf0

        if (CONFIG.log2ConsoleSwitch || CONFIG.log2FileSwitch || typeHigh == FILE) {
            if (typeLow < CONFIG.consoleFilter && typeLow < CONFIG.fileFilter) return

            val tagHead = processTagAndHead(tag)
            val body = processBody(typeHigh, *contents)

            if (CONFIG.log2ConsoleSwitch && typeHigh != FILE && typeLow >= CONFIG.consoleFilter) {
                print2Console(typeLow, tagHead.tag, tagHead.consoleHead, body)
            }

            if ((CONFIG.log2FileSwitch || typeHigh == FILE) && typeLow >= CONFIG.fileFilter) {
                EXECUTOR.execute { print2File(typeLow, tagHead.tag, tagHead.fileHead + body) }
            }
        }
    }

    private fun processTagAndHead(tag: String): TagHead {
        if (!CONFIG.tagIsSpace && !CONFIG.logHeadSwitch) {
            return TagHead(CONFIG.globalTag, null, ": ")
        }

        val stackTrace = Throwable().stackTrace
        val stackIndex = 3 + CONFIG.stackOffset

        if (stackIndex >= stackTrace.size) {
            val targetElement = stackTrace[3]
            val fileName = getFileName(targetElement)
            val finalTag =
                if (CONFIG.tagIsSpace && tag.isBlank()) {
                    val index = fileName.indexOf('.')
                    if (index == -1) fileName else fileName.substring(0, index)
                } else {
                    tag
                }
            return TagHead(finalTag, null, ": ")
        }

        val targetElement = stackTrace[stackIndex]
        val fileName = getFileName(targetElement)
        val finalTag =
            if (CONFIG.tagIsSpace && tag.isBlank()) {
                val index = fileName.indexOf('.')
                if (index == -1) fileName else fileName.substring(0, index)
            } else {
                tag
            }

        if (CONFIG.logHeadSwitch) {
            val tName = Thread.currentThread().name
            val head =
                String.format(
                    Locale.getDefault(),
                    "%s, %s.%s(%s:%d)",
                    tName,
                    targetElement.className,
                    targetElement.methodName,
                    fileName,
                    targetElement.lineNumber,
                )
            val fileHead = " [$head]: "

            if (CONFIG.stackDeep <= 1) {
                return TagHead(finalTag, arrayOf(head), fileHead)
            } else {
                val consoleHead =
                    Array(
                        kotlin.comparisons.minOf(CONFIG.stackDeep, stackTrace.size - stackIndex)
                    ) {
                        ""
                    }
                consoleHead[0] = head

                val spaceLen = tName.length + 2
                val space = String.format("%${spaceLen}s", "")

                for (i in 1 until consoleHead.size) {
                    val element = stackTrace[i + stackIndex]
                    consoleHead[i] =
                        String.format(
                            Locale.getDefault(),
                            "%s%s.%s(%s:%d)",
                            space,
                            element.className,
                            element.methodName,
                            getFileName(element),
                            element.lineNumber,
                        )
                }
                return TagHead(finalTag, consoleHead, fileHead)
            }
        }

        return TagHead(finalTag, null, ": ")
    }

    private fun getFileName(targetElement: StackTraceElement): String {
        var fileName = targetElement.fileName
        if (fileName != null) return fileName

        var className = targetElement.className
        val classNameInfo = className.split(".")
        if (classNameInfo.isNotEmpty()) {
            className = classNameInfo.last()
        }

        val index = className.indexOf('$')
        if (index != -1) {
            className = className.substring(0, index)
        }

        return "$className.kotlin"
    }

    private fun processBody(type: Int, vararg contents: Any?): String {
        var body = NULL
        if (contents.isNotEmpty()) {
            body =
                if (contents.size == 1) {
                    formatObject(type, contents[0])
                } else {
                    val sb = kotlin.text.StringBuilder()
                    contents.forEachIndexed { index, content ->
                        sb.append(ARGS)
                            .append("[")
                            .append(index)
                            .append("]")
                            .append(" = ")
                            .append(formatObject(content))
                            .append(LINE_SEP)
                    }
                    sb.toString()
                }
        }
        return body.ifEmpty { NOTHING }
    }

    private fun formatObject(type: Int, obj: Any?): String {
        if (obj == null) return NULL
        return when (type) {
            JSON -> LogFormatter.object2String(obj, JSON)
            XML -> LogFormatter.object2String(obj, XML)
            else -> formatObject(obj)
        }
    }

    private fun formatObject(obj: Any?): String {
        if (obj == null) return NULL

        if (I_FORMATTER_MAP.isEmpty().not()) {
            val iFormatter = I_FORMATTER_MAP[getClassFromObject(obj)]
            if (iFormatter != null) {
                @Suppress("UNCHECKED_CAST")
                return (iFormatter as IFormatter<Any>).format(obj)
            }
        }

        return LogFormatter.object2String(obj)
    }

    private fun print2Console(type: Int, tag: String, head: Array<String>?, msg: String) {
        if (CONFIG.singleTagSwitch) {
            printSingleTagMsg(type, tag, processSingleTagMsg(type, tag, head, msg))
        } else {
            printBorder(type, tag, true)
            printHead(type, tag, head)
            printMsg(type, tag, msg)
            printBorder(type, tag, false)
        }
    }

    private fun printBorder(type: Int, tag: String, isTop: Boolean) {
        if (CONFIG.logBorderSwitch) {
            print2Console(type, tag, if (isTop) TOP_BORDER else BOTTOM_BORDER)
        }
    }

    private fun printHead(type: Int, tag: String, head: Array<String>?) {
        head?.forEach { aHead ->
            print2Console(type, tag, if (CONFIG.logBorderSwitch) LEFT_BORDER + aHead else aHead)
        }
        if (CONFIG.logBorderSwitch) print2Console(type, tag, MIDDLE_BORDER)
    }

    private fun printMsg(type: Int, tag: String, msg: String) {
        if (msg.isEmpty()) {
            printSubMsg(type, tag, msg)
            return
        }

        val len = msg.length
        val countOfSub = len / MAX_LEN

        if (countOfSub > 0) {
            var index = 0
            for (i in 0 until countOfSub) {
                val endIndex = minOf(index + MAX_LEN, len)
                printSubMsg(type, tag, msg.substring(index, endIndex))
                index += MAX_LEN
            }
            if (index < len) {
                printSubMsg(type, tag, msg.substring(index, len))
            }
        } else {
            printSubMsg(type, tag, msg)
        }
    }

    private fun printSubMsg(type: Int, tag: String, msg: String) {
        if (!CONFIG.logBorderSwitch) {
            print2Console(type, tag, msg)
            return
        }

        val lines = msg.split(LINE_SEP)
        lines.forEach { line -> print2Console(type, tag, LEFT_BORDER + line) }
    }

    private fun processSingleTagMsg(
        type: Int,
        tag: String,
        head: Array<String>?,
        msg: String,
    ): String {
        val sb = kotlin.text.StringBuilder()
        if (CONFIG.logBorderSwitch) {
            sb.append(PLACEHOLDER).append(LINE_SEP)
            sb.append(TOP_BORDER).append(LINE_SEP)
            head?.forEach { aHead -> sb.append(LEFT_BORDER).append(aHead).append(LINE_SEP) }
            sb.append(MIDDLE_BORDER).append(LINE_SEP)
            msg.split(LINE_SEP).forEach { line ->
                sb.append(LEFT_BORDER).append(line).append(LINE_SEP)
            }
            sb.append(BOTTOM_BORDER)
        } else {
            head?.forEach { aHead ->
                sb.append(PLACEHOLDER).append(LINE_SEP)
                sb.append(aHead).append(LINE_SEP)
            }
            sb.append(msg)
        }
        return sb.toString()
    }

    private fun printSingleTagMsg(type: Int, tag: String, msg: String) {
        if (msg.isEmpty()) {
            print2Console(type, tag, msg)
            return
        }

        val len = msg.length
        val countOfSub =
            if (CONFIG.logBorderSwitch) {
                maxOf(0, (len - BOTTOM_BORDER.length) / MAX_LEN)
            } else {
                len / MAX_LEN
            }

        if (countOfSub > 0) {
            if (CONFIG.logBorderSwitch) {
                val firstPart = minOf(MAX_LEN, len)
                print2Console(type, tag, msg.substring(0, firstPart) + LINE_SEP + BOTTOM_BORDER)
                var index = MAX_LEN
                for (i in 1 until countOfSub) {
                    val endIndex = minOf(index + MAX_LEN, len)
                    print2Console(
                        type,
                        tag,
                        PLACEHOLDER +
                            LINE_SEP +
                            TOP_BORDER +
                            LINE_SEP +
                            LEFT_BORDER +
                            msg.substring(index, endIndex) +
                            LINE_SEP +
                            BOTTOM_BORDER,
                    )
                    index += MAX_LEN
                }
                if (index < len) {
                    print2Console(
                        type,
                        tag,
                        PLACEHOLDER +
                            LINE_SEP +
                            TOP_BORDER +
                            LINE_SEP +
                            LEFT_BORDER +
                            msg.substring(index, len),
                    )
                }
            } else {
                val firstPart = minOf(MAX_LEN, len)
                print2Console(type, tag, msg.substring(0, firstPart))
                var index = MAX_LEN
                for (i in 1 until countOfSub) {
                    val endIndex = minOf(index + MAX_LEN, len)
                    print2Console(
                        type,
                        tag,
                        PLACEHOLDER + LINE_SEP + msg.substring(index, endIndex),
                    )
                    index += MAX_LEN
                }
                if (index < len) {
                    print2Console(type, tag, PLACEHOLDER + LINE_SEP + msg.substring(index, len))
                }
            }
        } else {
            print2Console(type, tag, msg)
        }
    }

    private fun print2Console(type: Int, tag: String, msg: String) {
        Log.println(type, tag, msg)
        CONFIG.onConsoleOutputListener?.onConsoleOutput(type, tag, msg)
    }

    private fun print2File(type: Int, tag: String, msg: String) {
        val d = Date()
        val format = getSdf().format(d)
        val date = format.substring(0, 10)
        val currentLogFilePath = getCurrentLogFilePath(d)

        if (!createOrExistsFile(currentLogFilePath, date)) {
            Log.e("LogUtils", "create $currentLogFilePath failed!")
            return
        }

        val time = format.substring(11)
        val content = "$time${T[type - V]}/$tag$msg$LINE_SEP"
        input2File(currentLogFilePath, content)
    }

    private fun getCurrentLogFilePath(d: Date): String {
        val format = getSdf().format(d)
        val date = format.substring(0, 10)
        return "${CONFIG.dir}${CONFIG.filePrefix}_${date}_${CONFIG.processName}${CONFIG.fileExtension}"
    }

    private fun getSdf(): SimpleDateFormat {
        return simpleDateFormat.get()
            ?: SimpleDateFormat("yyyy_MM_dd HH:mm:ss.SSS ", Locale.getDefault())
    }

    private fun createOrExistsFile(filePath: String, date: String): Boolean {
        val file = File(filePath)
        if (file.exists()) return file.isFile()

        if (!UtilsBridge.createOrExistsDir(file.parentFile)) return false

        return try {
            deleteDueLogs(filePath, date)
            val isCreate = file.createNewFile()
            if (isCreate) {
                printDeviceInfo(filePath, date)
            }
            isCreate
        } catch (e: IOException) {
            e.printStackTrace()
            false
        }
    }

    private fun deleteDueLogs(filePath: String, date: String) {
        if (CONFIG.saveDays <= 0) return

        val file = File(filePath)
        val parentFile = file.parentFile
        val files = parentFile?.listFiles { _, name -> isMatchLogFileName(name) }

        if (files.isNullOrEmpty()) return

        try {
            val dateFormatInstance = dateFormat.get()
            if (dateFormatInstance == null) {
                Log.e("LogUtils", "Date format is null")
                return
            }

            val dueMillis =
                try {
                    dateFormatInstance.parse(date)?.time
                } catch (e: ParseException) {
                    Log.e("LogUtils", "Failed to parse date: $date", e)
                    return
                } ?: return

            val cutOffTime = dueMillis - CONFIG.saveDays * 86400000L

            files.forEach { aFile ->
                try {
                    val name = aFile.name
                    val logDay = findDate(name)
                    if (logDay.isNotEmpty()) {
                        val logDayTime =
                            try {
                                dateFormatInstance.parse(logDay)?.time
                            } catch (e: ParseException) {
                                Log.w("LogUtils", "Failed to parse log day: $logDay", e)
                                null
                            }
                        if (logDayTime != null && logDayTime <= cutOffTime) {
                            EXECUTOR.execute {
                                try {
                                    val delete = aFile.delete()
                                    if (!delete) {
                                        Log.e("LogUtils", "delete $aFile failed!")
                                    }
                                } catch (e: Exception) {
                                    Log.e("LogUtils", "Failed to delete file: $aFile", e)
                                }
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.w("LogUtils", "Failed to process file: ${aFile.name}", e)
                }
            }
        } catch (e: Exception) {
            Log.e("LogUtils", "Failed to delete due logs", e)
        }
    }

    private fun isMatchLogFileName(name: String): Boolean {
        return name.matches("^${CONFIG.filePrefix}_[0-9]{4}_[0-9]{2}_[0-9]{2}_.*$".toRegex())
    }

    private fun findDate(str: String): String {
        val pattern = Pattern.compile("[0-9]{4}_[0-9]{2}_[0-9]{2}")
        val matcher = pattern.matcher(str)
        return if (matcher.find()) matcher.group() else ""
    }

    private fun printDeviceInfo(filePath: String, date: String) {
        // 创建临时的 FileHead 避免多线程冲突
        synchronized(CONFIG.fileHead) {
            CONFIG.fileHead.addFirst("Date of Log", date)
            input2File(filePath, CONFIG.fileHead.toString())
        }
    }

    private fun input2File(filePath: String, input: String) {
        val fileWriter = CONFIG.fileWriter
        if (fileWriter == null) {
            UtilsBridge.writeFileFromString(filePath, input, true)
        } else {
            fileWriter.write(filePath, input)
        }
        CONFIG.onFileOutputListener?.onFileOutput(filePath, input)
    }

    class Config {
        var defaultDir: String = ""
        var dir: String? = null
        var filePrefix: String = "util"
        var fileExtension: String = ".txt"
        var logSwitch: Boolean = true
        var log2ConsoleSwitch: Boolean = true
        var globalTag: String = ""
        var tagIsSpace: Boolean = true
        var logHeadSwitch: Boolean = true
        var log2FileSwitch: Boolean = false
        var logBorderSwitch: Boolean = true
        var singleTagSwitch: Boolean = true
        var consoleFilter: Int = V
        var fileFilter: Int = V
        var stackDeep: Int = 1
        var stackOffset: Int = 0
        var saveDays: Int = -1
        var processName: String = UtilsBridge.getCurrentProcessName()
        var fileWriter: IFileWriter? = null
        var onConsoleOutputListener: OnConsoleOutputListener? = null
        var onFileOutputListener: OnFileOutputListener? = null
        var fileHead: FileHead = FileHead("Log")

        init {
            if (
                UtilsBridge.isSDCardEnableByEnvironment() &&
                    Utils.getApp().getExternalFilesDir(null) != null
            ) {
                defaultDir = "${Utils.getApp().getExternalFilesDir(null)}${FILE_SEP}log$FILE_SEP"
            } else {
                defaultDir = "${Utils.getApp().filesDir}${FILE_SEP}log$FILE_SEP"
            }
        }

        fun setLogSwitch(logSwitch: Boolean): Config {
            this.logSwitch = logSwitch
            return this
        }

        fun setConsoleSwitch(consoleSwitch: Boolean): Config {
            this.log2ConsoleSwitch = consoleSwitch
            return this
        }

        fun setGlobalTag(tag: String): Config {
            if (tag.isBlank()) {
                globalTag = ""
                tagIsSpace = true
            } else {
                globalTag = tag
                tagIsSpace = false
            }
            return this
        }

        fun setLogHeadSwitch(logHeadSwitch: Boolean): Config {
            this.logHeadSwitch = logHeadSwitch
            return this
        }

        fun setLog2FileSwitch(log2FileSwitch: Boolean): Config {
            this.log2FileSwitch = log2FileSwitch
            return this
        }

        fun setDir(dir: String?): Config {
            this.dir =
                if (dir.isNullOrBlank()) null
                else {
                    if (dir.endsWith(FILE_SEP)) dir else "$dir$FILE_SEP"
                }
            return this
        }

        fun setDir(dir: File?): Config {
            this.dir = dir?.absolutePath?.let { "$it$FILE_SEP" }
            return this
        }

        fun setFilePrefix(filePrefix: String): Config {
            this.filePrefix = filePrefix.ifBlank { "util" }
            return this
        }

        fun setFileExtension(fileExtension: String): Config {
            this.fileExtension =
                if (fileExtension.isBlank()) ".txt"
                else {
                    if (fileExtension.startsWith(".")) fileExtension else ".$fileExtension"
                }
            return this
        }

        fun setBorderSwitch(borderSwitch: Boolean): Config {
            this.logBorderSwitch = borderSwitch
            return this
        }

        fun setSingleTagSwitch(singleTagSwitch: Boolean): Config {
            this.singleTagSwitch = singleTagSwitch
            return this
        }

        fun setConsoleFilter(@TYPE consoleFilter: Int): Config {
            this.consoleFilter = consoleFilter
            return this
        }

        fun setFileFilter(@TYPE fileFilter: Int): Config {
            this.fileFilter = fileFilter
            return this
        }

        fun setStackDeep(stackDeep: Int): Config {
            this.stackDeep = stackDeep
            return this
        }

        fun setStackOffset(stackOffset: Int): Config {
            this.stackOffset = stackOffset
            return this
        }

        fun setSaveDays(saveDays: Int): Config {
            this.saveDays = saveDays
            return this
        }

        fun <T> addFormatter(iFormatter: IFormatter<T>?): Config {
            if (iFormatter != null) {
                val typeClass = getTypeClassFromParadigm(iFormatter)
                if (typeClass != null) {
                    @Suppress("UNCHECKED_CAST")
                    I_FORMATTER_MAP.put(typeClass, iFormatter as IFormatter<*>)
                }
            }
            return this
        }

        fun setFileWriter(fileWriter: IFileWriter?): Config {
            this.fileWriter = fileWriter
            return this
        }

        fun setOnConsoleOutputListener(listener: OnConsoleOutputListener?): Config {
            this.onConsoleOutputListener = listener
            return this
        }

        fun setOnFileOutputListener(listener: OnFileOutputListener?): Config {
            this.onFileOutputListener = listener
            return this
        }

        fun addFileExtraHead(fileExtraHead: Map<String, String>): Config {
            fileHead.append(fileExtraHead)
            return this
        }

        fun addFileExtraHead(key: String, value: String): Config {
            fileHead.append(key, value)
            return this
        }

        fun getProcessNameSafe(): String {
            return processName.replace(":", "_")
        }

        fun getDirSafe(): String = dir ?: defaultDir

        override fun toString(): String {
            return kotlin.text
                .StringBuilder()
                .apply {
                    append("process: ").append(getProcessNameSafe()).append(LINE_SEP)
                    append("logSwitch: ").append(logSwitch).append(LINE_SEP)
                    append("consoleSwitch: ").append(log2ConsoleSwitch).append(LINE_SEP)
                    append("tag: ").append(globalTag.ifEmpty { "null" }).append(LINE_SEP)
                    append("headSwitch: ").append(logHeadSwitch).append(LINE_SEP)
                    append("fileSwitch: ").append(log2FileSwitch).append(LINE_SEP)
                    append("dir: ").append(getDirSafe()).append(LINE_SEP)
                    append("filePrefix: ").append(filePrefix).append(LINE_SEP)
                    append("borderSwitch: ").append(logBorderSwitch).append(LINE_SEP)
                    append("singleTagSwitch: ").append(singleTagSwitch).append(LINE_SEP)
                    append("consoleFilter: ").append(T[consoleFilter - V]).append(LINE_SEP)
                    append("fileFilter: ").append(T[fileFilter - V]).append(LINE_SEP)
                    append("stackDeep: ").append(stackDeep).append(LINE_SEP)
                    append("stackOffset: ").append(stackOffset).append(LINE_SEP)
                    append("saveDays: ").append(saveDays).append(LINE_SEP)
                    append("formatter: ").append(I_FORMATTER_MAP).append(LINE_SEP)
                    append("fileWriter: ").append(fileWriter).append(LINE_SEP)
                    append("onConsoleOutputListener: ")
                        .append(onConsoleOutputListener)
                        .append(LINE_SEP)
                    append("onFileOutputListener: ").append(onFileOutputListener).append(LINE_SEP)
                    append("fileExtraHeader: ").append(fileHead.getAppended())
                }
                .toString()
        }
    }

    abstract class IFormatter<T> {
        abstract fun format(t: T): String
    }

    interface IFileWriter {
        fun write(file: String, content: String)
    }

    interface OnConsoleOutputListener {
        fun onConsoleOutput(@TYPE type: Int, tag: String, content: String)
    }

    interface OnFileOutputListener {
        fun onFileOutput(filePath: String, content: String)
    }

    class FileHead(val title: String) {
        private val mFirst = mutableListOf<String>()
        private val mLast = mutableListOf<String>()

        fun addFirst(key: String, value: String) {
            mFirst.add("$key: $value")
        }

        fun addLast(key: String, value: String) {
            mLast.add("$key: $value")
        }

        fun append(fileExtraHead: Map<String, String>) {
            if (fileExtraHead.isEmpty()) {
                return
            }
            for ((key, value) in fileExtraHead) {
                append(key, value)
            }
        }

        fun append(key: String, value: String) {
            if (key.isBlank() || value.isBlank()) {
                return
            }
            val delta = 19 - key.length // 19 is length of "Device Manufacturer"
            val paddedKey =
                if (delta > 0) {
                    key + "                   ".substring(0, delta)
                } else {
                    key
                }
            mLast.add("$paddedKey: $value")
        }

        fun getAppended(): String {
            return mLast.joinToString("\n")
        }

        override fun toString(): String {
            val sb = kotlin.text.StringBuilder()
            sb.append(
                "════════════════════════════════════════════════════════════════════════════════\n"
            )
            sb.append("Log Title: $title\n")
            for (msg in mFirst) {
                sb.append("$msg\n")
            }
            sb.append(
                "════════════════════════════════════════════════════════════════════════════════\n"
            )
            for (msg in mLast) {
                sb.append("$msg\n")
            }
            return sb.toString()
        }
    }

    private data class TagHead(
        val tag: String,
        val consoleHead: Array<String>?,
        val fileHead: String,
    ) {
        override fun equals(other: Any?): Boolean {
            if (this === other) return true
            if (javaClass != other?.javaClass) return false

            other as TagHead

            if (tag != other.tag) return false
            if (!consoleHead.contentEquals(other.consoleHead ?: emptyArray())) return false
            if (fileHead != other.fileHead) return false

            return true
        }

        override fun hashCode(): Int {
            var result = tag.hashCode()
            result = 31 * result + (consoleHead?.contentHashCode() ?: 0)
            result = 31 * result + fileHead.hashCode()
            return result
        }
    }

    private object LogFormatter {
        fun object2String(obj: Any?): String = object2String(obj, -1)

        fun object2String(obj: Any?, type: Int): String {
            if (obj == null) return NULL

            return when {
                obj.javaClass.isArray -> array2String(obj)
                obj is Throwable -> UtilsBridge.getFullStackTrace(obj)
                obj is Bundle -> bundle2String(obj)
                obj is Intent -> intent2String(obj)
                type == JSON -> object2Json(obj)
                type == XML -> formatXml(obj.toString())
                else -> obj.toString()
            }
        }

        @Suppress("DEPRECATION")
        private fun bundle2String(bundle: Bundle): String {
            val iterator = bundle.keySet().iterator()
            if (!iterator.hasNext()) return "Bundle {}"

            val sb = kotlin.text.StringBuilder(128)
            sb.append("Bundle { ")

            while (true) {
                val key = iterator.next()
                val value = bundle.get(key)
                sb.append(key).append('=')

                if (value is Bundle) {
                    sb.append(if (value == bundle) "(this Bundle)" else bundle2String(value))
                } else {
                    sb.append(formatObject(value))
                }

                if (!iterator.hasNext()) return sb.append(" }").toString()
                sb.append(',').append(' ')
            }
        }

        private fun intent2String(intent: Intent): String {
            val sb = kotlin.text.StringBuilder(128)
            sb.append("Intent { ")
            var first = true

            // Action
            intent.action?.let { action ->
                sb.append("act=").append(action)
                first = false
            }

            // Categories
            intent.categories?.let { categories ->
                if (!first) sb.append(' ')
                first = false
                sb.append("cat=[")
                sb.append(categories.joinToString(","))
                sb.append("]")
            }

            // Data
            intent.data?.let { data ->
                if (!first) sb.append(' ')
                first = false
                sb.append("dat=").append(data)
            }

            // Type
            intent.type?.let { type ->
                if (!first) sb.append(' ')
                first = false
                sb.append("typ=").append(type)
            }

            // Flags
            val flags = intent.flags
            if (flags != 0) {
                if (!first) sb.append(' ')
                first = false
                sb.append("flg=0x").append(Integer.toHexString(flags))
            }

            // Package
            intent.`package`?.let { pkg ->
                if (!first) sb.append(' ')
                first = false
                sb.append("pkg=").append(pkg)
            }

            // Component
            intent.component?.let { component ->
                if (!first) sb.append(' ')
                first = false
                sb.append("cmp=").append(component.flattenToShortString())
            }

            // Source Bounds
            intent.sourceBounds?.let { bounds ->
                if (!first) sb.append(' ')
                first = false
                sb.append("bnds=").append(bounds.toShortString())
            }

            // Clip Data
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN) {
                intent.clipData?.let { clipData ->
                    if (!first) sb.append(' ')
                    first = false
                    clipData2String(clipData, sb)
                }
            }

            // Extras
            intent.extras?.let { extras ->
                if (!first) sb.append(' ')
                first = false
                sb.append("extras={")
                sb.append(bundle2String(extras))
                sb.append('}')
            }

            // Selector
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.ICE_CREAM_SANDWICH_MR1) {
                intent.selector?.let { selector ->
                    if (!first) sb.append(' ')
                    first = false
                    sb.append("sel={")
                    sb.append(if (selector == intent) "(this Intent)" else intent2String(selector))
                    sb.append("}")
                }
            }

            sb.append(" }")
            return sb.toString()
        }

        @RequiresApi(Build.VERSION_CODES.JELLY_BEAN)
        private fun clipData2String(clipData: ClipData, sb: StringBuilder) {
            val item =
                clipData.getItemAt(0)
                    ?: run {
                        sb.append("ClipData.Item {}")
                        return
                    }

            sb.append("ClipData.Item { ")

            item.htmlText?.let { htmlText ->
                sb.append("H:").append(htmlText).append("}")
                return
            }

            item.text?.let { text ->
                sb.append("T:").append(text).append("}")
                return
            }

            item.uri?.let { uri ->
                sb.append("U:").append(uri).append("}")
                return
            }

            item.intent?.let { intent ->
                sb.append("I:").append(intent2String(intent)).append("}")
                return
            }

            sb.append("NULL").append("}")
        }

        private fun object2Json(obj: Any?): String {
            if (obj is CharSequence) {
                return formatJson(obj.toString())
            }

            return try {
                // 简单地将对象转换为字符串，然后格式化为JSON
                formatJson(obj.toString())
            } catch (t: Throwable) {
                obj.toString()
            }
        }

        private fun formatJson(json: String): String {
            return try {
                for (i in json.indices) {
                    val c = json[i]
                    when (c) {
                        '{' -> return JSONObject(json).toString(2)
                        '[' -> return JSONArray(json).toString(2)
                        else -> if (!c.isWhitespace()) return json
                    }
                }
                json
            } catch (e: JSONException) {
                e.printStackTrace()
                json
            }
        }

        private fun formatXml(xml: String): String {
            return try {
                val xmlInput: Source = StreamSource(StringReader(xml))
                val xmlOutput = StreamResult(StringWriter())
                val transformer = TransformerFactory.newInstance().newTransformer()
                transformer.setOutputProperty(OutputKeys.INDENT, "yes")
                transformer.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "2")
                transformer.transform(xmlInput, xmlOutput)
                xmlOutput.writer.toString().replaceFirst(">", ">$LINE_SEP")
            } catch (e: Exception) {
                e.printStackTrace()
                xml
            }
        }

        private fun array2String(obj: Any?): String {
            return when (obj) {
                is Array<*> -> obj.contentDeepToString()
                is BooleanArray -> obj.contentToString()
                is ByteArray -> obj.contentToString()
                is CharArray -> obj.contentToString()
                is DoubleArray -> obj.contentToString()
                is FloatArray -> obj.contentToString()
                is IntArray -> obj.contentToString()
                is LongArray -> obj.contentToString()
                is ShortArray -> obj.contentToString()
                else ->
                    throw kotlin.IllegalArgumentException(
                        "Array has incompatible type: ${obj?.javaClass}"
                    )
            }
        }
    }

    private fun <T> getTypeClassFromParadigm(formatter: IFormatter<T>): Class<*>? {
        val genericInterfaces = formatter.javaClass.genericInterfaces
        val type =
            if (genericInterfaces.size == 1) {
                genericInterfaces[0]
            } else {
                formatter.javaClass.genericSuperclass
            }

        val actualType = (type as ParameterizedType).actualTypeArguments[0]
        val finalType =
            when (actualType) {
                is ParameterizedType -> actualType.rawType
                else -> actualType
            }

        val className =
            finalType.toString().let { str ->
                when {
                    str.startsWith("class ") -> str.substring(6)
                    str.startsWith("interface ") -> str.substring(10)
                    else -> str
                }
            }

        return try {
            Class.forName(className)
        } catch (e: ClassNotFoundException) {
            e.printStackTrace()
            null
        }
    }

    private fun getClassFromObject(obj: Any?): Class<*> {
        val objClass = obj?.javaClass ?: return Any::class.java

        if (objClass.isAnonymousClass || objClass.isSynthetic) {
            val genericInterfaces = objClass.genericInterfaces
            val className =
                if (genericInterfaces.size == 1) {
                    // interface
                    var type = genericInterfaces[0]
                    while (type is ParameterizedType) {
                        type = type.rawType
                    }
                    type.toString()
                } else {
                    // abstract class or lambda
                    var type = objClass.genericSuperclass
                    while (type is ParameterizedType) {
                        type = type.rawType
                    }
                    type?.toString() ?: ""
                }

            val finalClassName =
                className.let { str ->
                    when {
                        str.startsWith("class ") -> str.substring(6)
                        str.startsWith("interface ") -> str.substring(10)
                        else -> str
                    }
                }

            return try {
                Class.forName(finalClassName)
            } catch (e: ClassNotFoundException) {
                e.printStackTrace()
                objClass
            }
        }

        return objClass
    }
}
