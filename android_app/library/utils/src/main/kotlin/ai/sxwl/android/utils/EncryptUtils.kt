package ai.sxwl.android.utils

import java.security.MessageDigest
import java.security.NoSuchAlgorithmException
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * 加密工具类
 * 提供加密相关的工具方法
 */
object EncryptUtils {

    /**
     * MD5加密
     */
    fun encryptMD5ToString(data: String?): String {
        if (data == null || data.isEmpty()) return ""
        return encryptMD5ToString(data.toByteArray())
    }

    /**
     * MD5加密
     */
    fun encryptMD5ToString(data: ByteArray?): String {
        return bytes2HexString(encryptMD5(data))
    }

    /**
     * MD5加密
     */
    fun encryptMD5(data: ByteArray?): ByteArray {
        return hashTemplate(data, "MD5")
    }

    /**
     * SHA1加密
     */
    fun encryptSHA1ToString(data: String?): String {
        if (data == null || data.isEmpty()) return ""
        return encryptSHA1ToString(data.toByteArray())
    }

    /**
     * SHA1加密
     */
    fun encryptSHA1ToString(data: ByteArray?): String {
        return bytes2HexString(encryptSHA1(data))
    }

    /**
     * SHA1加密
     */
    fun encryptSHA1(data: ByteArray?): ByteArray {
        return hashTemplate(data, "SHA1")
    }

    /**
     * SHA256加密
     */
    fun encryptSHA256ToString(data: String?): String {
        if (data == null || data.isEmpty()) return ""
        return encryptSHA256ToString(data.toByteArray())
    }

    /**
     * SHA256加密
     */
    fun encryptSHA256ToString(data: ByteArray?): String {
        return bytes2HexString(encryptSHA256(data))
    }

    /**
     * SHA256加密
     */
    fun encryptSHA256(data: ByteArray?): ByteArray {
        return hashTemplate(data, "SHA256")
    }

    /**
     * AES加密 (ECB模式)
     */
    fun encryptAES2Base64(data: String?, key: String?): String {
        if (data == null || data.isEmpty() || key == null || key.isEmpty()) return ""
        return EncodeUtils.base64Encode2String(encryptAES(data.toByteArray(), key.toByteArray()))
    }

    /**
     * AES加密 (ECB模式)
     */
    fun encryptAES(data: ByteArray?, key: ByteArray?): ByteArray {
        return desTemplate(data, key, "AES", "AES/ECB/PKCS5Padding", null, true)
    }

    /**
     * AES加密 (支持自定义transformation和IV)
     */
    fun encryptAES2Base64(
        data: ByteArray,
        key: ByteArray,
        transformation: String,
        iv: ByteArray?
    ): ByteArray? {
        return try {
            val encrypted = desTemplate(data, key, "AES", transformation, iv, true)
            EncodeUtils.base64Encode(encrypted)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * AES解密 (ECB模式)
     */
    fun decryptBase64AES(base64Data: String?, key: String?): String {
        if (base64Data == null || base64Data.isEmpty() || key == null || key.isEmpty()) return ""
        return String(decryptAES(EncodeUtils.base64Decode(base64Data), key.toByteArray()))
    }

    /**
     * AES解密 (ECB模式)
     */
    fun decryptAES(data: ByteArray?, key: ByteArray?): ByteArray {
        return desTemplate(data, key, "AES", "AES/ECB/PKCS5Padding", null, false)
    }

    /**
     * AES解密 (支持自定义transformation和IV)
     */
    fun decryptBase64AES(
        data: ByteArray,
        key: ByteArray,
        transformation: String,
        iv: ByteArray?
    ): ByteArray? {
        return try {
            val decoded = EncodeUtils.base64Decode(data)
            desTemplate(decoded, key, "AES", transformation, iv, false)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    ///////////////////////////////////////////////////////////////////////////
    // private methods
    ///////////////////////////////////////////////////////////////////////////

    private fun hashTemplate(data: ByteArray?, algorithm: String): ByteArray {
        if (data == null || data.isEmpty()) return ByteArray(0)
        return try {
            val md = MessageDigest.getInstance(algorithm)
            md.update(data)
            md.digest()
        } catch (e: NoSuchAlgorithmException) {
            e.printStackTrace()
            ByteArray(0)
        }
    }

    private fun desTemplate(
        data: ByteArray?,
        key: ByteArray?,
        algorithm: String,
        transformation: String,
        iv: ByteArray?,
        isEncrypt: Boolean
    ): ByteArray {
        if (data == null || data.isEmpty() || key == null || key.isEmpty()) return ByteArray(0)
        return try {
            val keySpec = SecretKeySpec(key, algorithm)
            val cipher = Cipher.getInstance(transformation)

            if (iv != null && iv.isNotEmpty()) {
                val ivSpec = IvParameterSpec(iv)
                cipher.init(
                    if (isEncrypt) Cipher.ENCRYPT_MODE else Cipher.DECRYPT_MODE,
                    keySpec,
                    ivSpec
                )
            } else {
                cipher.init(if (isEncrypt) Cipher.ENCRYPT_MODE else Cipher.DECRYPT_MODE, keySpec)
            }

            cipher.doFinal(data)
        } catch (e: Exception) {
            e.printStackTrace()
            ByteArray(0)
        }
    }

    private fun bytes2HexString(bytes: ByteArray?): String {
        if (bytes == null || bytes.isEmpty()) return ""
        val sb = kotlin.text.StringBuilder()
        for (b in bytes) {
            val hex = Integer.toHexString(0xFF and b.toInt())
            if (hex.length == 1) {
                sb.append('0')
            }
            sb.append(hex)
        }
        return sb.toString()
    }
}
