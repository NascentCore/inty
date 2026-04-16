import groovy.json.JsonSlurper
import java.io.File
import org.gradle.api.JavaVersion
import org.gradle.api.Project
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.hilt.android)
    alias(libs.plugins.ksp)
    alias(libs.plugins.kotlin.android)
}

private fun Project.imateSignDir(): File = rootProject.projectDir.resolve("sign")

private fun loadSigningCredentials(signDir: File, jsonKey: String): Triple<String, String, String> {
    val jsonFile = signDir.resolve("signing-config.json")
    check(jsonFile.exists()) { "Missing signing config: ${jsonFile.absolutePath}" }
    val parsed = JsonSlurper().parse(jsonFile) as Map<*, *>
    val m = parsed[jsonKey] as Map<*, *>
    val storePassword = m["storePassword"] as String
    val keyAlias = m["keyAlias"] as String
    val keyPassword = m["keyPassword"] as String
    return Triple(storePassword, keyAlias, keyPassword)
}

private fun Project.gitShortSha(): String = "debug"
//    providers
//        .exec {
//            commandLine("git", "rev-parse", "--short", "HEAD")
//            workingDir(rootProject.projectDir)
//        }
//        .standardOutput
//        .asText
//        .get()
//        .trim()

private fun Project.gitCommitCount(): Int = 1
//    providers
//        .exec {
//            commandLine("git", "rev-list", "--count", "HEAD")
//            workingDir(rootProject.projectDir)
//        }
//        .standardOutput
//        .asText
//        .get()
//        .trim()
//        .toInt()

android {
    namespace = "com.inty.imate"
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }

    val signDir = imateSignDir()
    val imateKeystoreFile = signDir.resolve("imate.jks")
    check(imateKeystoreFile.exists()) { "Missing keystore: ${imateKeystoreFile.absolutePath}" }
    val debugCred = loadSigningCredentials(signDir, "debug")
    val releaseCred = loadSigningCredentials(signDir, "release")

    defaultConfig {
        applicationId = "com.inty.imate"
        minSdk = 29
        targetSdk = 36
        versionCode = gitCommitCount()
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }
        ndk { abiFilters.add("arm64-v8a") }

        buildConfigField(
            "String",
            "WEB_CLIENT_ID",
            "\"1034291688895-f7eurgtisf1hhi16k4lti13g0grjtrit.apps.googleusercontent.com\"",
        )
    }

    signingConfigs {
        create("dev") {
            keyAlias = debugCred.second
            keyPassword = debugCred.third
            storePassword = debugCred.first
            storeFile = imateKeystoreFile
        }
        create("release") {
            keyAlias = releaseCred.second
            keyPassword = releaseCred.third
            storePassword = releaseCred.first
            storeFile = imateKeystoreFile
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            versionNameSuffix = "-${gitShortSha()}-$name"
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )

            buildConfigField(
                "String",
                "WEB_CLIENT_ID",
                "\"1034291688895-h5qhttfnanvv3c382aijomaqe9p7ei7f.apps.googleusercontent.com\"",
            )
        }
        debug {
            versionNameSuffix = "-${gitShortSha()}-$name"
            signingConfig = signingConfigs.getByName("dev")
        }
        create("playdebug") {
            initWith(getByName("release"))
            versionNameSuffix = "-${gitShortSha()}-$name"
        }
        create("local") {
            initWith(getByName("debug"))
            versionNameSuffix = "-${gitShortSha()}-$name"
        }
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            excludes += "/META-INF/DEPENDENCIES"
            excludes += "/META-INF/LICENSE"
            excludes += "/META-INF/LICENSE.txt"
            excludes += "/META-INF/NOTICE"
            excludes += "/META-INF/NOTICE.txt"
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11

    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_11)
    }
}

dependencies {
    implementation(project(":core"))

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)

    implementation(libs.androidx.navigation3.runtime)
    implementation(libs.androidx.navigation3.ui)
    implementation(libs.androidx.lifecycle.viewmodel.navigation3)
    implementation(libs.androidx.material3.adaptive.navigation3)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)

    implementation(platform(libs.ktor.bom))
    implementation(libs.ktor.client.android)
    implementation(libs.ktor.client.content.negotiation)
    implementation(libs.ktor.serialization.kotlinx.json)
    implementation(libs.okhttp)

    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    implementation(libs.androidx.room.paging)
    ksp(libs.androidx.room.compiler)

    implementation(libs.androidx.datastore.preferences)

    implementation(libs.androidx.paging.runtime)
    implementation(libs.androidx.paging.compose)

    implementation(libs.androidx.startup.runtime)

    implementation(libs.kotlinx.serialization.json)

    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)

    implementation(libs.google.identity.googleid)
    implementation(libs.androidx.credentials)
    implementation(libs.androidx.credentials.play.services)

    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
