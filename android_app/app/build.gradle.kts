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

android {
    namespace = "com.ai.inty"

    defaultConfig {
        applicationId = "com.ai.intellimate"
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

dependencies {
    // ===== Inty SDK（Stainless https://app.stainless.com/ 根据 app/openapi.json 生成的代码）=====
    // 使用本地 library/inty_sdk 的版本，避免动态版本在测试时的依赖解析问题
    implementation("com.inty.api:inty-kotlin:0.15.0")

    implementation(libs.androidx.appcompat)//ucropActivity需要
    implementation(libs.androidx.paging.compose)

    // ===== 项目模块 =====
    implementation(projects.core.common)
    implementation(projects.core.data)
    implementation(projects.core.design)
    implementation(projects.core.firebase)
    implementation(projects.library.network)
    implementation(projects.library.utils)

    // ===== 网络库 =====
    api(libs.retrofit.core)
    implementation(libs.retrofit2.kotlin.coroutines.adapter)
    // ===== 调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.no.op)
    "playdebugImplementation"(libs.chucker.no.op)

    // ===== 图片加载 =====
    implementation(libs.bundles.coil.bundle)

    // ===== Google 服务 =====
    implementation(libs.billing.client)
    implementation(platform(libs.firebase.bom))
    implementation(libs.bundles.firebase.core)
    implementation(libs.firebase.perf)
    implementation(libs.bundles.credentials)

    // ===== 图片处理 =====
    api(libs.ucrop)

    // ===== Media3 音频播放 =====
    implementation(libs.bundles.androidx.media3.bundle)
    implementation(libs.androidx.media3.datasource.okhttp)

}
