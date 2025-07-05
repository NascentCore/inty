import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    id("com.google.devtools.ksp") version "2.0.0-1.0.22"
    id("therouter")
    id("kotlin-parcelize")
    id("com.google.gms.google-services")
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
    val process = Runtime.getRuntime().exec("git rev-parse --short HEAD")
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
    compileSdk = 35

    defaultConfig {
        applicationId = "com.ai.inty"
        minSdk = 29
        targetSdk = 34
        versionCode = 3
        versionName = "1.0.0"

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
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    lint {
        checkReleaseBuilds=false
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

    debugImplementation (libs.library)
    releaseImplementation (libs.library.no.op)

    api(libs.retrofit.core)

    implementation(libs.retrofit2.kotlin.coroutines.adapter)
    implementation("io.coil-kt.coil3:coil-compose:3.2.0")
    implementation("io.coil-kt.coil3:coil-network-okhttp:3.2.0")

    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.analytics)
    implementation(libs.firebase.messaging)
    implementation(libs.firebase.messaging.directboot)
    implementation("com.google.android.gms:play-services-auth:21.2.0")

    api(libs.ucrop)
}