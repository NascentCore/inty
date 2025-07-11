plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp") version "2.2.0-2.0.2"
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
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

}


dependencies {

    //http log viewer
    debugImplementation(libs.chucker.library)
    releaseImplementation(libs.chucker.library.no.op)

    ksp(libs.moshi.kotlin.codegen)

    api(project(":utils"))
    api(libs.bundles.moshi)
}