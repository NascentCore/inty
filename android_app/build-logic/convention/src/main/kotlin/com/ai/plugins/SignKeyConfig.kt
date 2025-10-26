package com.ai.plugins

import com.google.gson.Gson
import java.io.File

/** 项目构建签名密钥的相关敏感参数，如密码等 */
object SignKeyConfig {

    data class SigningConfig(val debug: SigningInfo, val release: SigningInfo)

    data class SigningInfo(
        val storeFile: String,
        val storePassword: String,
        val keyAlias: String,
        val keyPassword: String,
    )

    private const val CONFIG_FILE_PATH = "build-logic/sign/signing-config.json"
    private val gson = Gson()

    /** 读取签名配置文件 */
    private fun loadSigningConfig(): SigningConfig {
        val configFile = File(CONFIG_FILE_PATH)
        if (!configFile.exists()) {
            throw IllegalStateException("签名配置文件不存在: $CONFIG_FILE_PATH")
        }

        val jsonContent = configFile.readText()
        return gson.fromJson(jsonContent, SigningConfig::class.java)
    }

    /** 获取签名配置 */
    private val signingConfig: SigningConfig by lazy { loadSigningConfig() }
// 调试签名配置常量
    val DEBUG_STORE_FILE: String
        get() = signingConfig.debug.storeFile

    val DEBUG_STORE_PASSWORD: String
        get() = signingConfig.debug.storePassword

    val DEBUG_KEY_ALIAS: String
        get() = signingConfig.debug.keyAlias

    val DEBUG_KEY_PASSWORD: String
        get() = signingConfig.debug.keyPassword
// 释放签名配置常量
    val RELEASE_STORE_FILE: String
        get() = signingConfig.release.storeFile

    val RELEASE_STORE_PASSWORD: String
        get() = signingConfig.release.storePassword

    val RELEASE_KEY_ALIAS: String
        get() = signingConfig.release.keyAlias

    val RELEASE_KEY_PASSWORD: String
        get() = signingConfig.release.keyPassword
}
