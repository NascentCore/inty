plugins {
    alias(libs.plugins.ai.android.application)
    alias(libs.plugins.ai.android.application.compose)
//    alias(libs.plugins.ai.android.application.flavor)
    alias(libs.plugins.ai.android.navigation.compose)

    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.kotlin.parcelize)
    alias(libs.plugins.google.services)
    alias(libs.plugins.firebase.crashlytics)
    alias(libs.plugins.ksp)

    id("therouter")

}

tasks.register("printVersionInfo") {
    group = "versioning"
    description = "Print version code and name"
    doLast {
        println("Version code: ${android.defaultConfig.versionCode}")
        println("Version name: ${android.defaultConfig.versionName}")
        println("Version name with suffix: ${android.defaultConfig.versionName}${android.defaultConfig.versionNameSuffix}")
    }
}

android {
    namespace = "com.ai.inty"

    defaultConfig {
        applicationId = "com.ai.intellimate"
        // Google OAuth client ID
        // TODO: This is the same now for debug and release builds for convenience.
        // Create a new client ID for debug build, but keep the production one for backward compatibility.
        // https://github.com/NascentCore/inty-backend/issues/171
        buildConfigField(
            "String",
            "WEB_CLIENT_ID",
            "\"1034291688895-0e5hq72pghd4nihhpmf989ptv0ag1542.apps.googleusercontent.com\""
        )
    }

    buildFeatures {
        buildConfig = true
    }

    packaging {
        resources {
            // 解决 META-INF 文件冲突问题
            // inty-sdk 包含了多个相同的文件
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            excludes += "/META-INF/DEPENDENCIES"
            excludes += "/META-INF/LICENSE"
            excludes += "/META-INF/LICENSE.txt"
            excludes += "/META-INF/NOTICE"
            excludes += "/META-INF/NOTICE.txt"
        }
    }
}

TheRouter {
    debug = false
    // 编译期检查路由表合法性，可选参数 warning(仅告警)/error(编译期抛异常)/delete(每次根据注解重新生成路由表)，不配置则不校验
    // checkRouteMap = "delete"
    // 检查 FlowTask 是否有循环引用，可选参数 warning(仅打印日志)/error(编译期抛异常)，不配置则不校验
    checkFlowDepend = "warning"
    // 图形化展示当前的 FlowTask 依赖图
    showFlowDepend = true
}

dependencies {
    // ===== AndroidX 核心库 =====
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.activity.ktx)
    implementation(libs.androidx.constraintlayout.compose)
    implementation(libs.androidx.paging.compose)

    // ===== 路由 =====
    implementation(libs.router)
    ksp(libs.therouter.apt)

    // ===== 项目模块 =====
    implementation(projects.library.utils)
    implementation(projects.library.network)

    // ===== 调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.no.op)
    "playdebugImplementation"(libs.chucker.no.op)

    // ===== 网络库 =====
    api(libs.retrofit.core)
    implementation(libs.retrofit2.kotlin.coroutines.adapter)

    // ===== 图片加载 =====
    implementation(libs.bundles.coil.bundle)

    // ===== Google 服务 =====
    implementation(libs.billing.client)
    implementation(platform(libs.firebase.bom))
    implementation(libs.bundles.firebase.core)
    implementation(libs.bundles.credentials)

    // ===== 图片处理 =====
    api(libs.ucrop)

    // ===== Media3 音频播放 =====
    implementation(libs.androidx.media3.datasource.okhttp)
    implementation(libs.bundles.androidx.media3.bundle)

    // ===== compose ui bundle =====
    implementation(libs.bundles.compose.ui.bundle)

    // ===== Inty SDK =====
    implementation("com.inty.api:inty-kotlin:0.8.0")
}
