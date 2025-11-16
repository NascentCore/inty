package ai.sxwl.android.utils

import android.content.Context
import android.content.pm.PackageManager
import android.content.pm.Signature
import android.os.Build
import android.util.Log
import java.io.ByteArrayInputStream
import java.io.InputStream
import java.security.MessageDigest
import java.security.NoSuchAlgorithmException
import java.security.cert.CertificateEncodingException
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate

/** 应用签名自校验工具类 */
class SignCheckTools(private val context: Context) {

    private val TAG = "SignCheckTools"
    private var cer: String? = null
    private var realCer: String? = null

    init {
        this.cer = getCertificateSHA1Fingerprint()
    }

    constructor(context: Context, realCer: String) : this(context) {
        this.realCer = realCer
        this.cer = getCertificateSHA1Fingerprint()
    }

    fun getRealCer(): String? = realCer

    /** 设置正确的签名 */
    fun setRealCer(realCer: String) {
        this.realCer = realCer
    }

    /** 获取应用的签名 */
    fun getCertificateSHA1Fingerprint(): String? {
        try {
            val signatures = loadSignatures() ?: return null
            if (signatures.isEmpty()) {
                Log.e(TAG, "未找到签名信息")
                return null
            }

            val cert = signatures[0].toByteArray()
            val input: InputStream = ByteArrayInputStream(cert)

            // 证书工厂类
            var cf: CertificateFactory? = null
            try {
                cf = CertificateFactory.getInstance("X509")
            } catch (e: Exception) {
                Log.e(TAG, "创建证书工厂失败", e)
                return null
            }

            // X509 证书
            var c: X509Certificate? = null
            try {
                c = cf?.generateCertificate(input) as? X509Certificate
                if (c == null) {
                    Log.e(TAG, "证书转换失败")
                    return null
                }
            } catch (e: ClassCastException) {
                Log.e(TAG, "证书类型转换失败", e)
                return null
            } catch (e: Exception) {
                Log.e(TAG, "生成证书失败", e)
                return null
            }

            var hexString: String? = null
            try {
                val md = MessageDigest.getInstance("SHA1")
                val publicKey = md.digest(c.encoded)
                hexString = byte2HexFormatted(publicKey)
            } catch (e1: NoSuchAlgorithmException) {
                Log.e(TAG, "SHA1算法不支持", e1)
                return null
            } catch (e: CertificateEncodingException) {
                Log.e(TAG, "证书编码失败", e)
                return null
            }

            return hexString
        } catch (e: Exception) {
            Log.e(TAG, "获取SHA1签名失败", e)
            return null
        }
    }

    /** 将字节数组转换为16进制字符串 */
    private fun byte2HexFormatted(arr: ByteArray): String {
        val str = kotlin.text.StringBuilder(arr.size * 2)

        for (i in arr.indices) {
            var h = Integer.toHexString(arr[i].toInt())
            val l = h.length
            if (l == 1) h = "0$h"
            if (l > 2) h = h.substring(l - 2, l)
            str.append(h.uppercase())
            if (i < arr.size - 1) str.append(':')
        }
        return str.toString()
    }

    /**
     * 检测签名是否正确
     *
     * @return true 签名正常 false 签名不正常
     */
    fun check(): Boolean {
        return if (realCer != null) {
            cer = cer?.trim()
            realCer = realCer?.trim()
            cer == realCer
        } else {
            Log.e(TAG, "未给定真实的签名 SHA-1 值")
            false
        }
    }

    /** 获取MD5签名 */
    fun getCertificateMD5Fingerprint(): String? {
        try {
            val signatures = loadSignatures() ?: return null
            if (signatures.isEmpty()) {
                Log.e(TAG, "未找到签名信息")
                return null
            }

            val cert = signatures[0].toByteArray()
            val input: InputStream = ByteArrayInputStream(cert)

            var cf: CertificateFactory? = null
            try {
                cf = CertificateFactory.getInstance("X509")
            } catch (e: Exception) {
                Log.e(TAG, "创建证书工厂失败", e)
                return null
            }

            var c: X509Certificate? = null
            try {
                c = cf?.generateCertificate(input) as? X509Certificate
                if (c == null) {
                    Log.e(TAG, "证书转换失败")
                    return null
                }
            } catch (e: ClassCastException) {
                Log.e(TAG, "证书类型转换失败", e)
                return null
            } catch (e: Exception) {
                Log.e(TAG, "生成证书失败", e)
                return null
            }

            var hexString: String? = null
            try {
                val md = MessageDigest.getInstance("MD5")
                val publicKey = md.digest(c.encoded)
                hexString = byte2HexFormatted(publicKey)
            } catch (e1: NoSuchAlgorithmException) {
                Log.e(TAG, "MD5算法不支持", e1)
                return null
            } catch (e: CertificateEncodingException) {
                Log.e(TAG, "证书编码失败", e)
                return null
            }

            return hexString
        } catch (e: Exception) {
            Log.e(TAG, "获取MD5签名失败", e)
            return null
        }
    }

    /** 获取SHA256签名 */
    fun getCertificateSHA256Fingerprint(): String? {
        try {
            val signatures = loadSignatures() ?: return null
            if (signatures.isEmpty()) {
                Log.e(TAG, "未找到签名信息")
                return null
            }

            val cert = signatures[0].toByteArray()
            val input: InputStream = ByteArrayInputStream(cert)

            var cf: CertificateFactory? = null
            try {
                cf = CertificateFactory.getInstance("X509")
            } catch (e: Exception) {
                Log.e(TAG, "创建证书工厂失败", e)
                return null
            }

            var c: X509Certificate? = null
            try {
                c = cf?.generateCertificate(input) as? X509Certificate
                if (c == null) {
                    Log.e(TAG, "证书转换失败")
                    return null
                }
            } catch (e: ClassCastException) {
                Log.e(TAG, "证书类型转换失败", e)
                return null
            } catch (e: Exception) {
                Log.e(TAG, "生成证书失败", e)
                return null
            }

            var hexString: String? = null
            try {
                val md = MessageDigest.getInstance("SHA256")
                val publicKey = md.digest(c.encoded)
                hexString = byte2HexFormatted(publicKey)
            } catch (e1: NoSuchAlgorithmException) {
                Log.e(TAG, "SHA256算法不支持", e1)
                return null
            } catch (e: CertificateEncodingException) {
                Log.e(TAG, "证书编码失败", e)
                return null
            }

            return hexString
        } catch (e: Exception) {
            Log.e(TAG, "获取SHA256签名失败", e)
            return null
        }
    }

    private fun loadSignatures(): Array<Signature>? {
        return try {
            val pm = context.packageManager
            val packageName = context.packageName
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val packageInfo =
                    pm.getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES)
                val signingInfo = packageInfo.signingInfo ?: return null
                if (signingInfo.hasMultipleSigners()) {
                    signingInfo.apkContentsSigners
                } else {
                    signingInfo.signingCertificateHistory
                }
            } else {
                @Suppress("DEPRECATION")
                val packageInfo = pm.getPackageInfo(packageName, PackageManager.GET_SIGNATURES)
                @Suppress("DEPRECATION") packageInfo?.signatures
            }
        } catch (e: PackageManager.NameNotFoundException) {
            Log.e(TAG, "包名未找到: ${context.packageName}", e)
            null
        } catch (e: Exception) {
            Log.e(TAG, "加载签名信息失败", e)
            null
        }
    }
}
