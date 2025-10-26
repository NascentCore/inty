package com.ai.plugins.ext

import com.ai.plugins.ProjectConfig
import com.ai.plugins.SignKeyConfig
import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.dsl.LibraryExtension
import java.io.File
import org.gradle.api.Project

/** 获取git提交信息的函数使用Provider来避免缓存配置问题 */
private fun getGitCommitInfo(project: Project): String {
    return project.providers
        .exec {
            commandLine("git", "rev-parse", "--short", "HEAD")
            workingDir(project.rootDir)
        }
        .standardOutput
        .asText
        .get()
        .trim()
}

/** 获取git的提交次数，作为versionCode 使用Provider来避免配置服务器问题 */
private fun getCommitCount(project: Project): Int {
    return project.providers
        .exec {
            commandLine("git", "rev-list", "--count", "HEAD")
            workingDir(project.rootDir)
        }
        .standardOutput
        .asText
        .get()
        .trim()
        .toInt()
}

/** android 应用gradle相关配置扩展函数 */
internal fun ApplicationExtension.commonAppConfig(project: Project) {
    defaultConfig {
        versionName = ProjectConfig.versionName
        versionCode = getCommitCount(project)
        targetSdk = ProjectConfig.targetVersion

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }
        ndk {
// 设置支持的SO库架构选择（开发者可以根据需要，一个或多个平台的所以） "armeabi", "armeabi-v7a", "arm64-v8a", "x86",
//“x86_64”
            abiFilters.add("arm64-v8a")
        }
    }
    signingConfigs {
        create("dev") {
            keyAlias = SignKeyConfig.DEBUG_KEY_ALIAS
            keyPassword = SignKeyConfig.DEBUG_KEY_PASSWORD
            storePassword = SignKeyConfig.DEBUG_STORE_PASSWORD
            storeFile = File("${project.rootDir}/build-logic/sign/intellimate-release-key.jks")
        }
        create("release") {
            keyAlias = SignKeyConfig.RELEASE_KEY_ALIAS
            keyPassword = SignKeyConfig.RELEASE_KEY_PASSWORD
            storePassword = SignKeyConfig.RELEASE_STORE_PASSWORD
            storeFile = File("${project.rootDir}/build-logic/sign/intellimate-release-key.jks")
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            versionNameSuffix = "-${getGitCommitInfo(project)}-$name"
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
        debug {
            versionNameSuffix = "-${getGitCommitInfo(project)}-$name"
            signingConfig = signingConfigs.getByName("dev")
            isMinifyEnabled = false
            isShrinkResources = false
        }

        create("playdebug") {
// 此版本旨在到 Google Play 进行调试。
// 它与开发框架对话，但应用程序是作为发布版本构建的。
            initWith(getByName("release"))
            isMinifyEnabled = false
            isShrinkResources = false
            versionNameSuffix = "-${getGitCommitInfo(project)}-$name"
        }

        create("local") {
            initWith(getByName("debug"))
            versionNameSuffix = "-${getGitCommitInfo(project)}-$name"
        }
    }

    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }
}

internal fun LibraryExtension.commonLibConfig() {
    defaultConfig {
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }

        consumerProguardFiles("consumer-rules.pro")
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
                "consumer-rules.pro",
            )
        }
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
                "consumer-rules.pro",
            )
        }
        create("playdebug") {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
                "consumer-rules.pro",
            )
        }
        create("local") {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
                "consumer-rules.pro",
            )
        }
    }

    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }
}
