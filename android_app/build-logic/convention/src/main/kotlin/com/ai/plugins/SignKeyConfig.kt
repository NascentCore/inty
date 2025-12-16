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
    private const val MAX_PARENT_LOOKUPS = 10
    private val gson = Gson()

    private fun findAndroidAppDir(): File {
        var dir: File? = File(System.getProperty("user.dir")).absoluteFile
        var remaining = MAX_PARENT_LOOKUPS
        while (dir != null && remaining > 0) {
            // 场景 1：当前就是 android_app/ 根目录（含 gradlew）
            if (File(dir, "gradlew").exists() && File(dir, "build-logic").exists()) {
                return dir
            }

            // 场景 2：当前在仓库根目录（含 android_app/ 子目录）
            val androidAppDir = File(dir, "android_app")
            if (File(androidAppDir, "gradlew").exists() && File(androidAppDir, "build-logic").exists()) {
                return androidAppDir
            }

            dir = dir.parentFile
            remaining -= 1
        }

        val cwd = File(System.getProperty("user.dir")).absoluteFile.path
        throw IllegalStateException("无法定位 android_app 目录 (cwd=$cwd)")
    }

    private fun findSigningConfigFile(): File {
        val androidAppDir = findAndroidAppDir()
        val configFile = File(androidAppDir, CONFIG_FILE_PATH)
        if (configFile.exists()) {
            return configFile
        }

        throw IllegalStateException("签名配置文件不存在: $CONFIG_FILE_PATH (androidAppDir=${androidAppDir.path})")
    }

    /** 读取签名配置文件 */
    private fun loadSigningConfig(): SigningConfig {
        val configFile = findSigningConfigFile()

        val jsonContent = configFile.readText()
        return gson.fromJson(jsonContent, SigningConfig::class.java)
    }

    /** 获取签名配置 */
    private val signingConfig: SigningConfig by lazy { loadSigningConfig() }

    // Debug 签名配置常量
    val DEBUG_STORE_FILE: String
        get() = signingConfig.debug.storeFile

    val DEBUG_STORE_PASSWORD: String
        get() = signingConfig.debug.storePassword

    val DEBUG_KEY_ALIAS: String
        get() = signingConfig.debug.keyAlias

    val DEBUG_KEY_PASSWORD: String
        get() = signingConfig.debug.keyPassword

    // Release 签名配置常量
    val RELEASE_STORE_FILE: String
        get() = signingConfig.release.storeFile

    val RELEASE_STORE_PASSWORD: String
        get() = signingConfig.release.storePassword

    val RELEASE_KEY_ALIAS: String
        get() = signingConfig.release.keyAlias

    val RELEASE_KEY_PASSWORD: String
        get() = signingConfig.release.keyPassword
}
