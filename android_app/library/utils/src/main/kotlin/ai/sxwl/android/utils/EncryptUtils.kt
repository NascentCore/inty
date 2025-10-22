package ai.sxwl.android.utils

import java.security.MessageDigest
import java.security.NoSuchAlgorithmException
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
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

    // ==================== 安全的AES加密方法 (CBC/GCM模式) ====================

    /**
     * AES-CBC加密 (推荐使用，比ECB更安全)
     * @param data 待加密数据
     * @param key 密钥 (16/24/32字节)
     * @return 加密结果，包含IV和密文
     */
    fun encryptAESCBC(data: String?, key: String?): String? {
        if (data == null || data.isEmpty() || key == null || key.isEmpty()) return null
        return encryptAESCBC(data.toByteArray(), key.toByteArray())?.let { result ->
            EncodeUtils.base64Encode2String(result)
        }
    }

    /**
     * AES-CBC加密 (推荐使用，比ECB更安全)
     * @param data 待加密数据
     * @param key 密钥 (16/24/32字节)
     * @return 加密结果，包含IV和密文
     */
    fun encryptAESCBC(data: ByteArray?, key: ByteArray?): ByteArray? {
        if (data == null || data.isEmpty() || key == null || key.isEmpty()) return null

        return try {
            // 生成随机IV
            val iv = ByteArray(16)
            SecureRandom().nextBytes(iv)

            // 加密数据
            val encrypted = desTemplate(data, key, "AES", "AES/CBC/PKCS5Padding", iv, true)

            // 将IV和密文组合
            ByteArray(iv.size + encrypted.size).apply {
                System.arraycopy(iv, 0, this, 0, iv.size)
                System.arraycopy(encrypted, 0, this, iv.size, encrypted.size)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * AES-CBC解密
     * @param encryptedData 加密数据 (包含IV和密文)
     * @param key 密钥
     * @return 解密结果
     */
    fun decryptAESCBC(encryptedData: ByteArray?, key: ByteArray?): ByteArray? {
        if (encryptedData == null || encryptedData.size < 16 || key == null || key.isEmpty()) return null

        return try {
            // 提取IV和密文
            val iv = ByteArray(16)
            val ciphertext = ByteArray(encryptedData.size - 16)
            System.arraycopy(encryptedData, 0, iv, 0, 16)
            System.arraycopy(encryptedData, 16, ciphertext, 0, ciphertext.size)

            // 解密
            desTemplate(ciphertext, key, "AES", "AES/CBC/PKCS5Padding", iv, false)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * AES-CBC解密 (Base64输入)
     * @param base64Data Base64编码的加密数据
     * @param key 密钥字符串
     * @return 解密结果字符串
     */
    fun decryptAESCBC(base64Data: String?, key: String?): String? {
        if (base64Data == null || base64Data.isEmpty() || key == null || key.isEmpty()) return null

        return try {
            val encryptedData = EncodeUtils.base64Decode(base64Data)
            val decrypted = decryptAESCBC(encryptedData, key.toByteArray())
            decrypted?.let { String(it) }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * AES-GCM加密 (最安全，支持认证加密)
     * @param data 待加密数据
     * @param key 密钥 (16/24/32字节)
     * @return 加密结果，包含IV和密文
     */
    fun encryptAESGCM(data: String?, key: String?): String? {
        if (data == null || data.isEmpty() || key == null || key.isEmpty()) return null
        return encryptAESGCM(data.toByteArray(), key.toByteArray())?.let { result ->
            EncodeUtils.base64Encode2String(result)
        }
    }

    /**
     * AES-GCM加密 (最安全，支持认证加密)
     * @param data 待加密数据
     * @param key 密钥 (16/24/32字节)
     * @return 加密结果，包含IV和密文
     */
    fun encryptAESGCM(data: ByteArray?, key: ByteArray?): ByteArray? {
        if (data == null || data.isEmpty() || key == null || key.isEmpty()) return null

        return try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            val keySpec = SecretKeySpec(key, "AES")

            // 生成随机IV (12字节用于GCM)
            val iv = ByteArray(12)
            SecureRandom().nextBytes(iv)

            // 初始化加密器
            val gcmSpec = GCMParameterSpec(128, iv) // 128位认证标签
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, gcmSpec)

            // 加密
            val encrypted = cipher.doFinal(data)

            // 将IV和密文组合
            ByteArray(iv.size + encrypted.size).apply {
                System.arraycopy(iv, 0, this, 0, iv.size)
                System.arraycopy(encrypted, 0, this, iv.size, encrypted.size)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * AES-GCM解密
     * @param encryptedData 加密数据 (包含IV和密文)
     * @param key 密钥
     * @return 解密结果
     */
    fun decryptAESGCM(encryptedData: ByteArray?, key: ByteArray?): ByteArray? {
        if (encryptedData == null || encryptedData.size < 12 || key == null || key.isEmpty()) return null

        return try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            val keySpec = SecretKeySpec(key, "AES")

            // 提取IV和密文
            val iv = ByteArray(12)
            val ciphertext = ByteArray(encryptedData.size - 12)
            System.arraycopy(encryptedData, 0, iv, 0, 12)
            System.arraycopy(encryptedData, 12, ciphertext, 0, ciphertext.size)

            // 初始化解密器
            val gcmSpec = GCMParameterSpec(128, iv)
            cipher.init(Cipher.DECRYPT_MODE, keySpec, gcmSpec)

            // 解密
            cipher.doFinal(ciphertext)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * AES-GCM解密 (Base64输入)
     * @param base64Data Base64编码的加密数据
     * @param key 密钥字符串
     * @return 解密结果字符串
     */
    fun decryptAESGCM(base64Data: String?, key: String?): String? {
        if (base64Data == null || base64Data.isEmpty() || key == null || key.isEmpty()) return null

        return try {
            val encryptedData = EncodeUtils.base64Decode(base64Data)
            val decrypted = decryptAESGCM(encryptedData, key.toByteArray())
            decrypted?.let { String(it) }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * 生成安全的随机密钥
     * @param keySize 密钥长度 (128/192/256位)
     * @return 随机密钥
     */
    fun generateSecureKey(keySize: Int = 256): ByteArray {
        val key = ByteArray(keySize / 8)
        SecureRandom().nextBytes(key)
        return key
    }

    /**
     * 生成安全的随机IV
     * @param ivSize IV长度 (通常为12或16字节)
     * @return 随机IV
     */
    fun generateSecureIV(ivSize: Int = 16): ByteArray {
        val iv = ByteArray(ivSize)
        SecureRandom().nextBytes(iv)
        return iv
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
