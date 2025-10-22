package ai.sxwl.android.utils

import java.io.BufferedOutputStream
import java.io.BufferedReader
import java.io.BufferedWriter
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.FileWriter
import java.io.InputStream
import java.io.InputStreamReader
import java.io.OutputStream

/**
 * 文件IO工具类
 * 提供文件IO相关的工具方法
 */
object FileIoUtils {

    private const val BUFFER_SIZE = 524288

    /**
     * 从输入流写入文件
     */
    fun writeFileFromIS(filePath: String?, inputStream: InputStream?): Boolean {
        return writeFileFromIS(FileUtils.getFileByPath(filePath), inputStream, false)
    }

    /**
     * 从输入流写入文件
     */
    fun writeFileFromIS(filePath: String?, inputStream: InputStream?, append: Boolean): Boolean {
        return writeFileFromIS(FileUtils.getFileByPath(filePath), inputStream, append)
    }

    /**
     * 从输入流写入文件
     */
    fun writeFileFromIS(file: File?, inputStream: InputStream?): Boolean {
        return writeFileFromIS(file, inputStream, false)
    }

    /**
     * 从输入流写入文件
     */
    fun writeFileFromIS(file: File?, inputStream: InputStream?, append: Boolean): Boolean {
        if (file == null || inputStream == null) return false
        if (!FileUtils.createOrExistsFile(file)) return false

        var os: OutputStream? = null
        try {
            os = BufferedOutputStream(FileOutputStream(file, append), BUFFER_SIZE)
            val data = ByteArray(BUFFER_SIZE)
            var len: Int
            while (inputStream.read(data, 0, BUFFER_SIZE).also { len = it } != -1) {
                os.write(data, 0, len)
            }
            return true
        } catch (e: Exception) {
            e.printStackTrace()
            return false
        } finally {
            try {
                inputStream.close()
                os?.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    /**
     * 读取文件到字符串
     */
    fun readFile2String(filePath: String?): String {
        return readFile2String(FileUtils.getFileByPath(filePath))
    }

    /**
     * 读取文件到字符串
     */
    fun readFile2String(filePath: String?, charsetName: String?): String {
        return readFile2String(FileUtils.getFileByPath(filePath), charsetName)
    }

    /**
     * 读取文件到字符串
     */
    fun readFile2String(file: File?): String {
        return readFile2String(file, "UTF-8")
    }

    /**
     * 读取文件到字符串
     */
    fun readFile2String(file: File?, charsetName: String?): String {
        if (file == null || !file.exists()) return ""

        var reader: BufferedReader? = null
        try {
            val sb = kotlin.text.StringBuilder()
            reader =
                BufferedReader(InputStreamReader(FileInputStream(file), charsetName ?: "UTF-8"))
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                sb.append(line).append("\n")
            }
            return sb.toString()
        } catch (e: Exception) {
            e.printStackTrace()
            return ""
        } finally {
            try {
                reader?.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    /**
     * 读取文件到字节数组
     */
    fun readFile2Bytes(filePath: String?): ByteArray {
        return readFile2Bytes(FileUtils.getFileByPath(filePath))
    }

    /**
     * 读取文件到字节数组
     */
    fun readFile2Bytes(file: File?): ByteArray {
        if (file == null || !file.exists()) return ByteArray(0)

        var inputStream: FileInputStream? = null
        try {
            inputStream = FileInputStream(file)
            val baos = ByteArrayOutputStream()
            val data = ByteArray(BUFFER_SIZE)
            var len: Int
            while (inputStream.read(data, 0, BUFFER_SIZE).also { len = it } != -1) {
                baos.write(data, 0, len)
            }
            return baos.toByteArray()
        } catch (e: Exception) {
            e.printStackTrace()
            return ByteArray(0)
        } finally {
            try {
                inputStream?.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    /**
     * 写入字符串到文件
     */
    fun writeFileFromString(filePath: String?, content: String?): Boolean {
        return writeFileFromString(FileUtils.getFileByPath(filePath), content, false)
    }

    /**
     * 写入字符串到文件
     */
    fun writeFileFromString(filePath: String?, content: String?, append: Boolean): Boolean {
        return writeFileFromString(FileUtils.getFileByPath(filePath), content, append)
    }

    /**
     * 写入字符串到文件
     */
    fun writeFileFromString(file: File?, content: String?): Boolean {
        return writeFileFromString(file, content, false)
    }

    /**
     * 写入字符串到文件
     */
    fun writeFileFromString(file: File?, content: String?, append: Boolean): Boolean {
        if (file == null || content == null) return false
        if (!FileUtils.createOrExistsFile(file)) return false

        var writer: BufferedWriter? = null
        try {
            writer = BufferedWriter(FileWriter(file, append))
            writer.write(content)
            return true
        } catch (e: Exception) {
            e.printStackTrace()
            return false
        } finally {
            try {
                writer?.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    /**
     * 写入字节数组到文件
     */
    fun writeFileFromBytes(filePath: String?, bytes: ByteArray?): Boolean {
        return writeFileFromBytes(FileUtils.getFileByPath(filePath), bytes, false)
    }

    /**
     * 写入字节数组到文件
     */
    fun writeFileFromBytes(filePath: String?, bytes: ByteArray?, append: Boolean): Boolean {
        return writeFileFromBytes(FileUtils.getFileByPath(filePath), bytes, append)
    }

    /**
     * 写入字节数组到文件
     */
    fun writeFileFromBytes(file: File?, bytes: ByteArray?): Boolean {
        return writeFileFromBytes(file, bytes, false)
    }

    /**
     * 写入字节数组到文件
     */
    fun writeFileFromBytes(file: File?, bytes: ByteArray?, append: Boolean): Boolean {
        if (file == null || bytes == null) return false
        if (!FileUtils.createOrExistsFile(file)) return false

        var os: OutputStream? = null
        try {
            os = BufferedOutputStream(FileOutputStream(file, append), BUFFER_SIZE)
            os.write(bytes)
            return true
        } catch (e: Exception) {
            e.printStackTrace()
            return false
        } finally {
            try {
                os?.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
