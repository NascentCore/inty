import com.google.firebase.crashlytics.buildtools.gradle.tasks.UploadMappingFileTask
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    alias(libs.plugins.ai.android.application)
    alias(libs.plugins.ai.android.application.compose)
    alias(libs.plugins.ai.android.navigation.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.kotlin.parcelize)
    alias(libs.plugins.google.services)
    alias(libs.plugins.firebase.crashlytics)
    alias(libs.plugins.firebase.perf)
    alias(libs.plugins.ksp)
}

tasks.register("printVersionInfo") {
    group = "versioning"
    description = "Print version code and name"
    doLast {
        println("Version code: ${android.defaultConfig.versionCode}")
        println("Version name: ${android.defaultConfig.versionName}")
        println(
            "Version name with suffix: ${android.defaultConfig.versionName}${android.defaultConfig.versionNameSuffix}"
        )
    }
}

private val crashlyticsUploadMarkerDir =
    layout.buildDirectory.dir("intermediates/crashlytics/mappingUploadMarkers")

tasks.withType<UploadMappingFileTask>().configureEach {
    val markerFile = crashlyticsUploadMarkerDir.map { dir -> dir.file("$name.marker") }
    outputs.file(markerFile)

    doLast {
        val file = markerFile.get().asFile
        file.parentFile.mkdirs()
        val variantName =
            name.removePrefix("uploadCrashlyticsMappingFile").replaceFirstChar {
                it.lowercaseChar()
            }
        file.writeText(
            buildString {
                    appendLine("task=$path")
                    appendLine("variant=$variantName")
                    appendLine("timestamp=${System.currentTimeMillis()}")
                }
                .trimEnd()
        )
    }
}

android {
    namespace = "com.ai.intellimate" // 这是代码命名空间，与代码package保持一致即可

    defaultConfig {
        applicationId = "com.ai.intellimate" // 这是app的唯一标识id，不可随意修改
        // Google OAuth client ID
        // TODO: This is the same now for debug and release builds for convenience.
        // Create a new client ID for debug build, but keep the production one for backward
        // compatibility.
        // https://github.com/NascentCore/inty-backend/issues/171
        buildConfigField(
            "String",
            "WEB_CLIENT_ID",
            "\"1034291688895-0e5hq72pghd4nihhpmf989ptv0ag1542.apps.googleusercontent.com\"",
        )
    }

    buildFeatures { buildConfig = true }

    packaging {
        resources {
            // 解决 META-INF 文件冲突问题
            // inty-sdk 包含了多个同名文件
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            excludes += "/META-INF/DEPENDENCIES"
            excludes += "/META-INF/LICENSE"
            excludes += "/META-INF/LICENSE.txt"
            excludes += "/META-INF/NOTICE"
            excludes += "/META-INF/NOTICE.txt"
        }
    }
}

tasks.withType<KotlinCompile>().configureEach {
    compilerOptions {
        freeCompilerArgs.assign(listOf("-XXLanguage:+PropertyParamAnnotationDefaultTargetMode"))
    }
}

dependencies {
    implementation(libs.androidx.appcompat) // ucropActivity需要
    implementation(libs.androidx.paging.compose)
    implementation(libs.androidx.compose.material.icons.extended)

    // ===== Inty SDK（用于 ReportReasonMappings 等直接使用 SDK 类型的代码）=====
    // 注意：版本必须与 core/data/build.gradle.kts 保持一致，统一在 libs.versions.toml 中管理
    implementation(libs.inty.kotlin)

    // ===== 存储库 =====
    // 为角色应援/Boost 功能提供本地数据存储
    // TODO：考虑将其移动到 core/data 模块中，因为其是本地数据存储，不属于 app 模块。
    implementation(libs.mmkv)

    // ===== 项目模块 =====
    implementation(projects.core.common)
    implementation(projects.core.data)
    implementation(projects.core.design)
    implementation(projects.core.firebase)
    implementation(projects.library.network)
    implementation(projects.library.utils)

    // ===== 图片加载 =====
    implementation(libs.bundles.coil.bundle)

    // ===== Google 服务 =====
    implementation(libs.bundles.credentials)

    // ===== 图片处理 =====
    implementation(libs.ucrop)

    // ===== Media3 音频播放 =====
    implementation(libs.bundles.androidx.media3.bundle)
    implementation(libs.androidx.media3.datasource.okhttp)

    // ===== UI 测试依赖 =====
    androidTestImplementation(libs.androidx.uiautomator)

    // ===== 背景/前景虚化库 =====
    // https://chrisbanes.github.io/haze/latest/usage/
    implementation(libs.haze)
}
