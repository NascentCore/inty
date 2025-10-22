package ai.sxwl.android.utils

import android.content.Context
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.content.pm.Signature
import android.util.Log
import java.io.ByteArrayInputStream
import java.io.InputStream
import java.security.MessageDigest
import java.security.NoSuchAlgorithmException
import java.security.cert.CertificateEncodingException
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate

/**
 * 应用签名自校验工具类
 */
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

    /**
     * 设置正确的签名
     */
    fun setRealCer(realCer: String) {
        this.realCer = realCer
    }

    /**
     * 获取应用的签名
     */
    fun getCertificateSHA1Fingerprint(): String? {
        // 获取包管理器
        val pm = context.packageManager

        // 获取当前要获取 SHA1 值的包名
        val packageName = context.packageName

        // 返回包括在包中的签名信息
        val flags = PackageManager.GET_SIGNATURES

        var packageInfo: PackageInfo? = null

        try {
            // 获得包的所有内容信息类
            packageInfo = pm.getPackageInfo(packageName, flags)
        } catch (e: PackageManager.NameNotFoundException) {
            e.printStackTrace()
        }

        // 签名信息
        val signatures: Array<Signature> = packageInfo?.signatures ?: return null
        val cert = signatures[0].toByteArray()

        // 将签名转换为字节数组流
        val input: InputStream = ByteArrayInputStream(cert)

        // 证书工厂类
        var cf: CertificateFactory? = null

        try {
            cf = CertificateFactory.getInstance("X509")
        } catch (e: Exception) {
            e.printStackTrace()
        }

        // X509 证书
        var c: X509Certificate? = null

        try {
            c = cf?.generateCertificate(input) as X509Certificate
        } catch (e: Exception) {
            e.printStackTrace()
        }

        var hexString: String? = null

        try {
            // 加密算法的类
            val md = MessageDigest.getInstance("SHA1")

            // 获得公钥
            val publicKey = md.digest(c?.encoded)

            // 字节到十六进制的格式转换
            hexString = byte2HexFormatted(publicKey)
        } catch (e1: NoSuchAlgorithmException) {
            e1.printStackTrace()
        } catch (e: CertificateEncodingException) {
            e.printStackTrace()
        }

        return hexString
    }

    /**
     * 将字节数组转换为16进制字符串
     */
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

    /**
     * 获取MD5签名
     */
    fun getCertificateMD5Fingerprint(): String? {
        val pm = context.packageManager
        val packageName = context.packageName
        val flags = PackageManager.GET_SIGNATURES

        var packageInfo: PackageInfo? = null

        try {
            packageInfo = pm.getPackageInfo(packageName, flags)
        } catch (e: PackageManager.NameNotFoundException) {
            e.printStackTrace()
        }

        val signatures: Array<Signature> = packageInfo?.signatures ?: return null
        val cert = signatures[0].toByteArray()
        val input: InputStream = ByteArrayInputStream(cert)

        var cf: CertificateFactory? = null
        try {
            cf = CertificateFactory.getInstance("X509")
        } catch (e: Exception) {
            e.printStackTrace()
        }

        var c: X509Certificate? = null
        try {
            c = cf?.generateCertificate(input) as X509Certificate
        } catch (e: Exception) {
            e.printStackTrace()
        }

        var hexString: String? = null
        try {
            val md = MessageDigest.getInstance("MD5")
            val publicKey = md.digest(c?.encoded)
            hexString = byte2HexFormatted(publicKey)
        } catch (e1: NoSuchAlgorithmException) {
            e1.printStackTrace()
        } catch (e: CertificateEncodingException) {
            e.printStackTrace()
        }

        return hexString
    }

    /**
     * 获取SHA256签名
     */
    fun getCertificateSHA256Fingerprint(): String? {
        val pm = context.packageManager
        val packageName = context.packageName
        val flags = PackageManager.GET_SIGNATURES

        var packageInfo: PackageInfo? = null

        try {
            packageInfo = pm.getPackageInfo(packageName, flags)
        } catch (e: PackageManager.NameNotFoundException) {
            e.printStackTrace()
        }

        val signatures: Array<Signature> = packageInfo?.signatures ?: return null
        val cert = signatures[0].toByteArray()
        val input: InputStream = ByteArrayInputStream(cert)

        var cf: CertificateFactory? = null
        try {
            cf = CertificateFactory.getInstance("X509")
        } catch (e: Exception) {
            e.printStackTrace()
        }

        var c: X509Certificate? = null
        try {
            c = cf?.generateCertificate(input) as X509Certificate
        } catch (e: Exception) {
            e.printStackTrace()
        }

        var hexString: String? = null
        try {
            val md = MessageDigest.getInstance("SHA256")
            val publicKey = md.digest(c?.encoded)
            hexString = byte2HexFormatted(publicKey)
        } catch (e1: NoSuchAlgorithmException) {
            e1.printStackTrace()
        } catch (e: CertificateEncodingException) {
            e.printStackTrace()
        }

        return hexString
    }
}
