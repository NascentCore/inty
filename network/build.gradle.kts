plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.architecture.httplib"
    compileSdk = 36

    defaultConfig {
        minSdk = 29

    }


    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        create("playdebug") {
            initWith(getByName("release"))
        }
        create("local") {
            initWith(getByName("debug"))
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    
    kotlin {
        jvmToolchain(21)
    }
}


dependencies {
    // ===== 调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.library.no.op)
    "playdebugImplementation"(libs.chucker.library.no.op)

    // ===== JSON 序列化 =====
    ksp(libs.moshi.kotlin.codegen)

    // ===== 项目模块 =====
    api(project(":utils"))
    api(libs.bundles.moshi)
}