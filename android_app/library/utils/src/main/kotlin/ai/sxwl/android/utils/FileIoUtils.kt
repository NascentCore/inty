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
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            writeFileFromIS(file, inputStream, false)
        } else {
            false
        }
    }

    /**
     * 从输入流写入文件
     */
    fun writeFileFromIS(filePath: String?, inputStream: InputStream?, append: Boolean): Boolean {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            writeFileFromIS(file, inputStream, append)
        } else {
            false
        }
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

        return try {
            if (!FileUtils.createOrExistsFile(file)) return false

            var os: OutputStream? = null
            try {
                os = BufferedOutputStream(FileOutputStream(file, append), BUFFER_SIZE)
                val data = ByteArray(BUFFER_SIZE)
                var len: Int
                while (inputStream.read(data, 0, BUFFER_SIZE).also { len = it } != -1) {
                    os.write(data, 0, len)
                }
                true
            } finally {
                try {
                    inputStream.close()
                } catch (e: Exception) {
                    // 静默处理关闭异常
                }
                try {
                    os?.close()
                } catch (e: Exception) {
                    // 静默处理关闭异常
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * 读取文件到字符串
     */
    fun readFile2String(filePath: String?): String {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            readFile2String(file)
        } else {
            ""
        }
    }

    /**
     * 读取文件到字符串
     */
    fun readFile2String(filePath: String?, charsetName: String?): String {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            readFile2String(file, charsetName)
        } else {
            ""
        }
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
            val charset = try {
                charsetName ?: "UTF-8"
            } catch (e: Exception) {
                "UTF-8" // 默认使用UTF-8
            }

            reader = BufferedReader(InputStreamReader(FileInputStream(file), charset))
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
                // 静默处理关闭异常
            }
        }
    }

    /**
     * 读取文件到字节数组
     */
    fun readFile2Bytes(filePath: String?): ByteArray {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            readFile2Bytes(file)
        } else {
            ByteArray(0)
        }
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
        } catch (e: OutOfMemoryError) {
            // 内存不足，返回空数组
            return ByteArray(0)
        } catch (e: Exception) {
            e.printStackTrace()
            return ByteArray(0)
        } finally {
            try {
                inputStream?.close()
            } catch (e: Exception) {
                // 静默处理关闭异常
            }
        }
    }

    /**
     * 写入字符串到文件
     */
    fun writeFileFromString(filePath: String?, content: String?): Boolean {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            writeFileFromString(file, content, false)
        } else {
            false
        }
    }

    /**
     * 写入字符串到文件
     */
    fun writeFileFromString(filePath: String?, content: String?, append: Boolean): Boolean {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            writeFileFromString(file, content, append)
        } else {
            false
        }
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

        return try {
            if (!FileUtils.createOrExistsFile(file)) return false

            var writer: BufferedWriter? = null
            try {
                writer = BufferedWriter(FileWriter(file, append))
                writer.write(content)
                true
            } finally {
                try {
                    writer?.close()
                } catch (e: Exception) {
                    // 静默处理关闭异常
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * 写入字节数组到文件
     */
    fun writeFileFromBytes(filePath: String?, bytes: ByteArray?): Boolean {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            writeFileFromBytes(file, bytes, false)
        } else {
            false
        }
    }

    /**
     * 写入字节数组到文件
     */
    fun writeFileFromBytes(filePath: String?, bytes: ByteArray?, append: Boolean): Boolean {
        val file = FileUtils.getFileByPath(filePath)
        return if (file != null) {
            writeFileFromBytes(file, bytes, append)
        } else {
            false
        }
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

        return try {
            if (!FileUtils.createOrExistsFile(file)) return false

            var os: OutputStream? = null
            try {
                os = BufferedOutputStream(FileOutputStream(file, append), BUFFER_SIZE)
                os.write(bytes)
                true
            } finally {
                try {
                    os?.close()
                } catch (e: Exception) {
                    // 静默处理关闭异常
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
}
