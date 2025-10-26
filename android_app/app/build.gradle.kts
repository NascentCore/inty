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
    namespace = "com.ai.intellimate"//这是代码命名空间，与代码package保持一致即可

    defaultConfig {
        applicationId = "com.ai.intellimate"//这是app的唯一标识id，不可随意修改
// Google OAuth 客户端 ID
// TODO：为了方便起见，这对于调试和发布版本来说是相同的。
// 为调试构建创建一个新的客户端ID，但保留prduction以便刚性使用
// 兼容性。
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

    implementation(libs.androidx.appcompat)//ucropActivity需要
    implementation(libs.androidx.paging.compose)
// ===== 项目模块 =====
    implementation(projects.core.common)
    implementation(projects.core.data)
    implementation(projects.core.design)
    implementation(projects.core.firebase)
    implementation(projects.library.network)
    implementation(projects.library.utils)
// ===== 图片加载 =====
    implementation(libs.bundles.coil.bundle)
// ===== 谷歌服务 =====
    implementation(libs.bundles.credentials)
// ===== 图片处理 =====
    implementation(libs.ucrop)
// ===== Media3 音频播放 =====
    implementation(libs.bundles.androidx.media3.bundle)
    implementation(libs.androidx.media3.datasource.okhttp)

}
