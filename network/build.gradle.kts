plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp") version "2.0.0-1.0.22"
}

android {

    namespace = "com.architecture.httplib"
    compileSdk = 35

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
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

}


dependencies {

    //http log viewer
    debugImplementation (libs.library)
    releaseImplementation (libs.library.no.op)

    ksp(libs.moshi.kotlin.codegen)
    api(project(":utils"))
    api(libs.bundles.moshi)
}