import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    id("com.google.devtools.ksp") version "2.2.0-2.0.2"
    id("therouter")
    id("kotlin-parcelize")

    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
    id("com.google.firebase.firebase-perf")
}

// 安全加载 keystore.properties
val keystorePropertiesFile = rootProject.file("keystore.properties")
if (!keystorePropertiesFile.exists()) {
    throw GradleException("Missing keystore.properties file in project root")
}
val keystoreProperties = Properties()
keystoreProperties.load(FileInputStream(keystorePropertiesFile))

fun requireProperty(props: Properties, key: String): String {
    return props.getProperty(key) ?: throw GradleException("Missing property: $key")
}

val gitCommitId = try {
    val process = ProcessBuilder("git", "rev-parse", "--short", "HEAD").start()
    process.waitFor()
    if (process.exitValue() == 0) {
        process.inputStream.bufferedReader().readText().trim()
    } else {
        "2fbffaf"  // 当前commit ID作为fallback
    }
} catch (e: Exception) {
    "2fbffaf"  // 当前commit ID作为fallback
}

android {
    namespace = "com.ai.inty"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.ai.heartmate"
        minSdk = 29
        targetSdk = 36
        versionCode = 6
        versionName = "1.0.1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // 添加BuildConfig字段用于调试
        buildConfigField("String", "GIT_COMMIT_ID", "\"$gitCommitId\"")
        buildConfigField("boolean", "IS_DEBUG_BUILD", "false")

        // 数据安全声明 - 不使用广告ID
        manifestPlaceholders["uses_ads"] = "false"
        vectorDrawables {
            useSupportLibrary = true
        }
        ndk {
            abiFilters.clear()
            abiFilters.add("arm64-v8a")
        }
    }
    signingConfigs {
        create("inty") {
            storeFile = rootProject.file(requireProperty(keystoreProperties, "debug.storeFile"))
            storePassword = requireProperty(keystoreProperties, "debug.storePassword")
            keyAlias = requireProperty(keystoreProperties, "debug.keyAlias")
            keyPassword = requireProperty(keystoreProperties, "debug.keyPassword")
        }
        create("release") {
            storeFile = rootProject.file(requireProperty(keystoreProperties, "release.storeFile"))
            storePassword = requireProperty(keystoreProperties, "release.storePassword")
            keyAlias = requireProperty(keystoreProperties, "release.keyAlias")
            keyPassword = requireProperty(keystoreProperties, "release.keyPassword")
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            ndk {
                debugSymbolLevel = "FULL" // 或者 'SYMBOL_TABLE'
            }
        }
        debug {
            signingConfig = signingConfigs.getByName("inty")
            versionNameSuffix = " ($gitCommitId)"
            buildConfigField("boolean", "IS_DEBUG_BUILD", "true")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    buildFeatures {
        compose = true
        buildConfig = true
        // 启用其他有用的功能
        viewBinding = false
        dataBinding = false
    }


    lint {
        checkReleaseBuilds = false
        // 添加更多检查选项
        abortOnError = false
        checkOnly += "NewApi"
    }

}

TheRouter {
    debug = false
    // 编译期检查路由表合法性，可选参数 warning(仅告警)/error(编译期抛异常)/delete(每次根据注解重新生成路由表)，不配置则不校验
//    checkRouteMap = "delete"
    // 检查 FlowTask 是否有循环引用，可选参数 warning(仅打印日志)/error(编译期抛异常)，不配置则不校验
    checkFlowDepend = "warning"
    // 图形化展示当前的 FlowTask 依赖图
    showFlowDepend = true
}

dependencies {

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)

    implementation(libs.androidx.material3)

    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)


    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)


    implementation(libs.router)
    ksp(libs.therouter.apt)

    implementation(project(":utils"))
    implementation(project(":network"))

    debugImplementation(libs.chucker.library)
    releaseImplementation(libs.chucker.library.no.op)

    api(libs.retrofit.core)

    implementation(libs.retrofit2.kotlin.coroutines.adapter)
    // 统一使用 Coil 3.x 版本
    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)

    //Google支付
    implementation(libs.billing.ktx)
    //google 登录授权
    implementation(libs.play.services.auth)
    //firebase 相关依赖
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.analytics)
    implementation(libs.firebase.messaging)
    implementation(libs.firebase.messaging.directboot)
    implementation(libs.firebase.crashlytics)
    implementation(libs.firebase.perf)

    api(libs.ucrop)
}