package ai.sxwl.android.utils

import android.app.Application
import android.os.Build
import android.util.Log
import androidx.core.net.toUri
import java.io.File
import java.io.FileFilter
import java.io.FileInputStream
import java.io.FileNotFoundException
import java.io.FileOutputStream
import java.io.IOException
import java.security.DigestInputStream
import java.security.MessageDigest
import java.util.Locale

/** 文件工具类 提供文件操作相关的工具方法 */
object FileUtils {

    /** 根据文件路径获取文件 */
    fun getFileByPath(filePath: String?): File? {
        return if (UtilsBridge.isSpace(filePath)) null else File(filePath!!)
    }

    /** 判断文件是否存在 */
    fun isFileExists(file: File?): Boolean {
        if (file == null) return false
        if (file.exists()) return true
        return isFileExists(file.absolutePath)
    }

    /** 判断文件是否存在 */
    fun isFileExists(filePath: String?): Boolean {
        val file = getFileByPath(filePath)
        if (file == null) return false
        if (file.exists()) return true
        return isFileExistsApi29(filePath)
    }

    private fun isFileExistsApi29(filePath: String?): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                val uri = filePath?.toUri() ?: return false
                val context: Application? = Utils.getApp()
                if (context == null) {
                    Log.e("FileUtils", "Context为null，无法检查文件存在性: $filePath")
                    return false
                }

                val cr = context.contentResolver
                val afd = cr.openAssetFileDescriptor(uri, "r")
                if (afd == null) return false

                try {
                    afd.close()
                } catch (e: IOException) {
                    Log.w("FileUtils", "关闭AssetFileDescriptor异常: $filePath", e)
                }
                return true
            } catch (e: SecurityException) {
                Log.e("FileUtils", "检查文件存在性权限异常: $filePath", e)
                return false
            } catch (e: FileNotFoundException) {
                return false
            } catch (e: Exception) {
                Log.e("FileUtils", "检查文件存在性异常: $filePath", e)
                return false
            }
        }
        return false
    }

    /** 重命名文件 */
    fun rename(filePath: String?, newName: String?): Boolean {
        return rename(getFileByPath(filePath), newName)
    }

    /** 重命名文件 */
    fun rename(file: File?, newName: String?): Boolean {
        if (file == null) return false
        if (!file.exists()) return false
        if (UtilsBridge.isSpace(newName)) return false
        if (newName == file.name) return true

        val parentDir = file.parent
        if (parentDir == null) {
            Log.e("FileUtils", "文件父目录为null: ${file.absolutePath}")
            return false
        }

        val newFile = File(parentDir + File.separator + newName)
        return try {
            !newFile.exists() && file.renameTo(newFile)
        } catch (e: SecurityException) {
            Log.e("FileUtils", "文件重命名权限异常: ${file.absolutePath}", e)
            false
        } catch (e: Exception) {
            Log.e("FileUtils", "文件重命名异常: ${file.absolutePath}", e)
            false
        }
    }

    /** 判断是否为目录 */
    fun isDir(file: File?): Boolean {
        return file != null && file.exists() && file.isDirectory
    }

    /** 判断是否为目录 */
    fun isDir(filePath: String?): Boolean {
        return isDir(getFileByPath(filePath))
    }

    /** 判断是否为文件 */
    fun isFile(file: File?): Boolean {
        return file != null && file.exists() && file.isFile
    }

    /** 判断是否为文件 */
    fun isFile(filePath: String?): Boolean {
        return isFile(getFileByPath(filePath))
    }

    /** 创建或存在目录 */
    fun createOrExistsDir(dir: File?): Boolean {
        return dir != null && (dir.exists() && dir.isDirectory || dir.mkdirs())
    }

    /** 创建或存在目录 */
    fun createOrExistsDir(dirPath: String?): Boolean {
        return createOrExistsDir(getFileByPath(dirPath))
    }

    /** 创建或存在文件 */
    fun createOrExistsFile(file: File?): Boolean {
        if (file == null) return false
        if (file.exists()) return file.isFile
        if (!createOrExistsDir(file.parentFile)) return false
        return try {
            file.createNewFile()
        } catch (e: Exception) {
            false
        }
    }

    /** 创建或存在文件 */
    fun createOrExistsFile(filePath: String?): Boolean {
        return createOrExistsFile(getFileByPath(filePath))
    }

    /** 创建文件，如果存在则删除旧文件 */
    fun createFileByDeleteOldFile(filePath: String?): Boolean {
        return createFileByDeleteOldFile(getFileByPath(filePath))
    }

    /** 创建文件，如果存在则删除旧文件 */
    fun createFileByDeleteOldFile(file: File?): Boolean {
        if (file == null) return false
        if (file.exists() && !file.delete()) return false
        if (!createOrExistsDir(file.parentFile)) return false
        return try {
            file.createNewFile()
        } catch (e: Exception) {
            false
        }
    }

    /** 复制文件或目录 */
    fun copy(srcPath: String?, destPath: String?): Boolean {
        return copy(getFileByPath(srcPath), getFileByPath(destPath), null)
    }

    /** 复制文件或目录 */
    fun copy(srcPath: String?, destPath: String?, listener: OnReplaceListener?): Boolean {
        return copy(getFileByPath(srcPath), getFileByPath(destPath), listener)
    }

    /** 复制文件或目录 */
    fun copy(src: File?, dest: File?): Boolean {
        return copy(src, dest, null)
    }

    /** 复制文件或目录 */
    fun copy(src: File?, dest: File?, listener: OnReplaceListener?): Boolean {
        if (src == null) return false
        return if (src.isDirectory) {
            copyDir(src, dest, listener)
        } else {
            copyFile(src, dest, listener)
        }
    }

    private fun copyDir(srcDir: File, destDir: File?, listener: OnReplaceListener?): Boolean {
        return copyOrMoveDir(srcDir, destDir, listener, false)
    }

    private fun copyFile(srcFile: File, destFile: File?, listener: OnReplaceListener?): Boolean {
        return copyOrMoveFile(srcFile, destFile, listener, false)
    }

    /** 移动文件或目录 */
    fun move(srcPath: String?, destPath: String?): Boolean {
        return move(getFileByPath(srcPath), getFileByPath(destPath), null)
    }

    /** 移动文件或目录 */
    fun move(srcPath: String?, destPath: String?, listener: OnReplaceListener?): Boolean {
        return move(getFileByPath(srcPath), getFileByPath(destPath), listener)
    }

    /** 移动文件或目录 */
    fun move(src: File?, dest: File?): Boolean {
        return move(src, dest, null)
    }

    /** 移动文件或目录 */
    fun move(src: File?, dest: File?, listener: OnReplaceListener?): Boolean {
        if (src == null) return false
        return if (src.isDirectory) {
            moveDir(src, dest, listener)
        } else {
            moveFile(src, dest, listener)
        }
    }

    private fun moveDir(srcDir: File, destDir: File?, listener: OnReplaceListener?): Boolean {
        return copyOrMoveDir(srcDir, destDir, listener, true)
    }

    private fun moveFile(srcFile: File, destFile: File?, listener: OnReplaceListener?): Boolean {
        return copyOrMoveFile(srcFile, destFile, listener, true)
    }

    private fun copyOrMoveDir(srcDir: File, destDir: File?, listener: OnReplaceListener?): Boolean {
        return copyOrMoveDir(srcDir, destDir, listener, false)
    }

    private fun copyOrMoveDir(
        srcDir: File,
        destDir: File?,
        listener: OnReplaceListener?,
        isMove: Boolean
    ): Boolean {
        if (destDir == null) return false
        if (destDir.exists()) {
            if (listener?.onReplace(srcDir, destDir) == true) {
                if (!deleteDir(destDir)) return false
            } else {
                return false
            }
        }
        if (!createOrExistsDir(destDir)) return false
        val files = srcDir.listFiles() ?: return false
        for (file in files) {
            val oneDestFile = File(destDir, file.name)
            if (file.isFile) {
                if (!copyOrMoveFile(file, oneDestFile, listener, isMove)) return false
            } else if (file.isDirectory) {
                if (!copyOrMoveDir(file, oneDestFile, listener, isMove)) return false
            }
        }
        return !isMove || deleteDir(srcDir)
    }

    private fun copyOrMoveFile(
        srcFile: File,
        destFile: File?,
        listener: OnReplaceListener?
    ): Boolean {
        return copyOrMoveFile(srcFile, destFile, listener, false)
    }

    private fun copyOrMoveFile(
        srcFile: File,
        destFile: File?,
        listener: OnReplaceListener?,
        isMove: Boolean
    ): Boolean {
        if (destFile == null) return false
        if (destFile.exists()) {
            if (listener?.onReplace(srcFile, destFile) == true) {
                if (!destFile.delete()) return false
            } else {
                return false
            }
        }
        if (!createOrExistsDir(destFile.parentFile)) return false
        return try {
            FileInputStream(srcFile).use { inputStream ->
                FileOutputStream(destFile).use { outputStream ->
                    val buffer = ByteArray(8192)
                    var len: Int
                    while (inputStream.read(buffer).also { len = it } != -1) {
                        outputStream.write(buffer, 0, len)
                    }
                    outputStream.flush()
                }
            }
            !isMove || srcFile.delete()
        } catch (e: SecurityException) {
            Log.e("FileUtils", "文件复制权限异常: ${srcFile.absolutePath}", e)
            false
        } catch (e: IOException) {
            Log.e("FileUtils", "文件复制IO异常: ${srcFile.absolutePath}", e)
            false
        } catch (e: Exception) {
            Log.e("FileUtils", "文件复制异常: ${srcFile.absolutePath}", e)
            false
        }
    }

    /** 删除文件 */
    fun deleteFile(file: File?): Boolean {
        return file != null && (!file.exists() || file.isFile && file.delete())
    }

    /** 删除文件 */
    fun deleteFile(filePath: String?): Boolean {
        return deleteFile(getFileByPath(filePath))
    }

    /** 删除目录 */
    fun deleteDir(dir: File?): Boolean {
        if (dir == null) return false
        if (!dir.exists()) return true
        if (!dir.isDirectory) return false
        val files = dir.listFiles() ?: return false
        for (file in files) {
            if (file.isFile) {
                if (!file.delete()) return false
            } else if (file.isDirectory) {
                if (!deleteDir(file)) return false
            }
        }
        return dir.delete()
    }

    /** 删除目录 */
    fun deleteDir(dirPath: String?): Boolean {
        return deleteDir(getFileByPath(dirPath))
    }

    /** 获取文件大小 */
    fun getFileSize(file: File?): Long {
        return if (file == null || !file.exists()) {
            -1
        } else if (file.isDirectory) getDirLength(file) else file.length()
    }

    /** 获取文件大小 */
    fun getFileSize(filePath: String?): Long {
        return getFileSize(getFileByPath(filePath))
    }

    /** 获取目录大小 */
    private fun getDirLength(dir: File): Long {
        var len = 0L
        val files = dir.listFiles() ?: return len
        for (file in files) {
            len += if (file.isDirectory) getDirLength(file) else file.length()
        }
        return len
    }

    /** 获取文件大小的格式化字符串 */
    fun getFileSizeFormat(file: File?): String {
        return formatFileSize(getFileSize(file))
    }

    /** 获取文件大小的格式化字符串 */
    fun getFileSizeFormat(filePath: String?): String {
        return getFileSizeFormat(getFileByPath(filePath))
    }

    /** 格式化文件大小 */
    fun formatFileSize(size: Long): String {
        return when {
            size < 0 -> "Invalid size"
            size < 1024 -> "$size B"
            size < 1024 * 1024 -> String.format(Locale.getDefault(), "%.1f KB", size / 1024.0)
            size < 1024 * 1024 * 1024 ->
                String.format(Locale.getDefault(), "%.1f MB", size / (1024.0 * 1024.0))
            else -> String.format(Locale.getDefault(), "%.1f GB", size / (1024.0 * 1024.0 * 1024.0))
        }
    }

    /** 获取文件MD5值 */
    fun getFileMD5(filePath: String?): String? {
        return getFileMD5(getFileByPath(filePath))
    }

    /** 获取文件MD5值 */
    fun getFileMD5(file: File?): String? {
        return getFileMD5ToString(file)
    }

    /** 获取文件MD5值 */
    fun getFileMD5ToString(filePath: String?): String? {
        return getFileMD5ToString(getFileByPath(filePath))
    }

    /** 获取文件MD5值 */
    fun getFileMD5ToString(file: File?): String? {
        return getFileMD5ToString(file, "MD5")
    }

    /** 获取文件MD5值 */
    fun getFileMD5ToString(file: File?, algorithm: String): String? {
        if (file == null) return null
        return try {
            val md = MessageDigest.getInstance(algorithm)
            FileInputStream(file).use { inputStream ->
                DigestInputStream(inputStream, md).use { digestInputStream ->
                    val buffer = ByteArray(8192)
                    while (digestInputStream.read(buffer) != -1) {
                        // 读取文件内容，计算MD5
                    }
                }
            }
            val digest = md.digest()
            val hexString = kotlin.text.StringBuilder()
            for (b in digest) {
                val hex = Integer.toHexString(0xFF and b.toInt())
                if (hex.length == 1) {
                    hexString.append('0')
                }
                hexString.append(hex)
            }
            hexString.toString()
        } catch (e: SecurityException) {
            Log.e("FileUtils", "计算MD5权限异常: ${file.absolutePath}", e)
            null
        } catch (e: IOException) {
            Log.e("FileUtils", "计算MD5 IO异常: ${file.absolutePath}", e)
            null
        } catch (e: Exception) {
            Log.e("FileUtils", "计算MD5异常: ${file.absolutePath}", e)
            null
        }
    }

    /** 获取文件最后修改时间 */
    fun getFileLastModified(filePath: String?): Long {
        return getFileLastModified(getFileByPath(filePath))
    }

    /** 获取文件最后修改时间 */
    fun getFileLastModified(file: File?): Long {
        return file?.lastModified() ?: -1
    }

    /** 获取文件MIME类型 */
    fun getMimeType(filePath: String?): String? {
        return getMimeType(getFileByPath(filePath))
    }

    /** 获取文件MIME类型 */
    fun getMimeType(file: File?): String? {
        if (file == null) return null
        return try {
            val url = file.toURI().toURL()
            val connection = url.openConnection()
            connection.connectTimeout = 5000
            connection.readTimeout = 5000
            connection.contentType
        } catch (e: Exception) {
            null
        }
    }

    /** 获取文件扩展名 */
    fun getFileExtension(filePath: String?): String? {
        return getFileExtension(getFileByPath(filePath))
    }

    /** 获取文件扩展名 */
    fun getFileExtension(file: File?): String? {
        if (file == null) return null
        val fileName = file.name
        val lastDotIndex = fileName.lastIndexOf('.')
        return if (lastDotIndex >= 0) fileName.substring(lastDotIndex + 1) else null
    }

    /** 获取文件名（不含扩展名） */
    fun getFileNameWithoutExtension(filePath: String?): String? {
        return getFileNameWithoutExtension(getFileByPath(filePath))
    }

    /** 获取文件名（不含扩展名） */
    fun getFileNameWithoutExtension(file: File?): String? {
        if (file == null) return null
        val fileName = file.name
        val lastDotIndex = fileName.lastIndexOf('.')
        return if (lastDotIndex >= 0) fileName.substring(0, lastDotIndex) else fileName
    }

    /** 写入字符串到文件 */
    fun writeFileFromString(filePath: String?, content: String?, append: Boolean): Boolean {
        return writeFileFromString(getFileByPath(filePath), content, append)
    }

    /** 写入字符串到文件 */
    fun writeFileFromString(file: File?, content: String?, append: Boolean): Boolean {
        if (file == null || content == null) return false
        if (!createOrExistsFile(file)) return false
        return try {
            if (append) {
                file.appendText(content)
            } else {
                file.writeText(content)
            }
            true
        } catch (e: SecurityException) {
            Log.e("FileUtils", "写入文件权限异常: ${file.absolutePath}", e)
            false
        } catch (e: IOException) {
            Log.e("FileUtils", "写入文件IO异常: ${file.absolutePath}", e)
            false
        } catch (e: Exception) {
            Log.e("FileUtils", "写入文件异常: ${file.absolutePath}", e)
            false
        }
    }

    /** 从文件读取字符串 */
    fun readFile2String(filePath: String?): String? {
        return readFile2String(getFileByPath(filePath))
    }

    /** 从文件读取字符串 */
    fun readFile2String(file: File?): String? {
        if (file == null || !file.exists()) return null
        return try {
            file.readText()
        } catch (e: SecurityException) {
            Log.e("FileUtils", "读取文件权限异常: ${file.absolutePath}", e)
            null
        } catch (e: IOException) {
            Log.e("FileUtils", "读取文件IO异常: ${file.absolutePath}", e)
            null
        } catch (e: Exception) {
            Log.e("FileUtils", "读取文件异常: ${file.absolutePath}", e)
            null
        }
    }

    /** 获取目录下的所有文件 */
    fun listFilesInDir(dirPath: String?): List<File>? {
        return listFilesInDir(getFileByPath(dirPath))
    }

    /** 获取目录下的所有文件 */
    fun listFilesInDir(dir: File?): List<File>? {
        if (dir == null || !dir.exists() || !dir.isDirectory) return null
        val files = dir.listFiles() ?: return null
        return files.toList()
    }

    /** 获取目录下的所有文件（递归） */
    fun listFilesInDirWithFilter(dirPath: String?, filter: FileFilter?): List<File>? {
        return listFilesInDirWithFilter(getFileByPath(dirPath), filter)
    }

    /** 获取目录下的所有文件（递归） */
    fun listFilesInDirWithFilter(dir: File?, filter: FileFilter?): List<File>? {
        if (dir == null || !dir.exists() || !dir.isDirectory) return null
        val files = dir.listFiles(filter) ?: return null
        return files.toList()
    }

    /** 文件替换监听器 */
    interface OnReplaceListener {
        fun onReplace(srcFile: File, destFile: File): Boolean
    }
}
