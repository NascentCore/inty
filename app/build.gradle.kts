import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    id("com.google.devtools.ksp") version "2.2.0-2.0.2"
    id("therouter")
    id("kotlin-parcelize")

    alias(libs.plugins.google.services)
    alias(libs.plugins.firebase.crashlytics)
    alias(libs.plugins.firebase.perf)
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

val gitCommitId = {
    val process = ProcessBuilder("git", "rev-parse", "--short", "HEAD").start()
    process.waitFor()
    if (process.exitValue() != 0) {
        throw GradleException("Git commit id failed")
    }
    process.inputStream.bufferedReader().readText().trim()
}

// 返回 git commit count 作为自增的 version code.
fun getVersionCode(): Int {
    val process = ProcessBuilder("git", "rev-list", "--count", "HEAD").start()
    process.waitFor()
    if (process.exitValue() != 0) {
        throw GradleException("Git commit count failed")
    }
    val gitCommitCount = process.inputStream.bufferedReader().readText().trim().toInt()
    println("🚀 VERSION CODE: $gitCommitCount (based on git commits) for build type: ${project.gradle.startParameter.taskNames.joinToString()}")
    return gitCommitCount
}

// Add task to print both version code and name with suffix
tasks.register("printVersionWithSuffix") {
    group = "versioning"
    description = "Print both version code and name with git commit suffix"
    doLast {
        println("Version Code: ${getVersionCode()}")
        println("Version Name with Suffix: 1.1.0 ($gitCommitId)")
    }
}

android {
    namespace = "com.ai.inty"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.ai.intellimate"
        minSdk = 29
        targetSdk = 36

        // When release a new aab, increase this version code by 1.
        // This is different from version name, which is public to users.
        // This is used by Google Play to determine which binary is newer or older.
        // This should never decrease.
        //
        // Do not increase this for development builds.
        // Only google play uses this.
        // Largest version code is 2100000000
        // https://developer.android.com/studio/publish/versioning.html
        versionCode = getVersionCode()

        // Version name follows Semantic Versioning 2.0.0 (https://semver.org/).
        //
        // Public version, refers the version name seen by public users.
        // It's also a tag applied to main or release branches (if fix commits are done after tagging).
        //
        // New public versions, can only increase minor (middle) digit of the version name.
        // Or rarely, increase the major (first) digit.
        //
        // Dev version, refers to a name uniquely identify a commit on the main branch.
        // It's now uses YYYYMMDD-HHMMSS format, applied during the cron schedule in github workflow.
        //
        // To release a new public version, we increase fix (third) digit of the version name.
        // Each time we upload a new binary for a release version, 1.1.x,
        // we need to increase the fix digit, and create a new tag for that binary.
        //
        // Bug fix public release, code changes are applied on the versioned branch.
        versionName = "1.1.1"

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
            versionNameSuffix = " ($gitCommitId)"
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            ndk {
                // https://developer.android.com/build/include-native-symbols
                debugSymbolLevel = "FULL"
            }
        }
        create("playdebug") {
            // This build is meant to be pushed to Google Play for debugging.
            // It talks to the dev backend, but app is built as release.
            initWith(getByName("release"))
        }
        // TODO: Consider rename this to staging, meaning it's talking to the staging backend,
        // which is not local.
        debug {
            // This build talks to the staging backend.
            signingConfig = signingConfigs.getByName("inty")
            versionNameSuffix = " ($gitCommitId)"
            buildConfigField("boolean", "IS_DEBUG_BUILD", "true")
        }
        create("local") {
            initWith(getByName("debug"))
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    buildFeatures {
        compose = true
        buildConfig = true
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
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.library.no.op)
    "playdebugImplementation"(libs.chucker.library.no.op)

    api(libs.retrofit.core)

    implementation(libs.retrofit2.kotlin.coroutines.adapter)
    // 统一使用 Coil 3.x 版本
    implementation(libs.bundles.coils3)

    // Google支付
    implementation(libs.billing.ktx)

    // 新的身份验证方式
    implementation(libs.credential.manager)
    implementation(libs.credential.play.service.auth)
    implementation(libs.google.identity)
    //firebase 相关依赖
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.analytics)
    implementation(libs.firebase.messaging)
    implementation(libs.firebase.messaging.directboot)
    implementation(libs.firebase.crashlytics)
    implementation(libs.firebase.perf)

    api(libs.ucrop)

    // 协程支持
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
}

// GitHub Actions直接从构建文件和Git历史中提取版本信息，不再需要专门的Gradle任务
