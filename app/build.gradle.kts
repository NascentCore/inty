import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
    id("therouter")
    kotlin("plugin.parcelize")

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

val gitCommitId = providers.exec {
    commandLine("git", "rev-parse", "--short", "HEAD")
    workingDir = projectDir
}.standardOutput.asText.get().trim()

// 返回 git commit count 作为自增的 version code.
fun getCommitCount(): Int {
    val process = ProcessBuilder("git", "rev-list", "--count", "HEAD").start()
    process.waitFor()
    if (process.exitValue() != 0) {
        throw GradleException("Git commit count failed")
    }
    val gitCommitCount = process.inputStream.bufferedReader().readText().trim().toInt()
    println("🚀 VERSION CODE: $gitCommitCount (based on git commits) for build type: ${project.gradle.startParameter.taskNames.joinToString()}")
    return gitCommitCount
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
        versionCode = getCommitCount()

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
        //
        // TODO: Can this be set in a external file so that the app and backend share this version?
        // No, we don't want to share version between app and backend, as backend can move faster.
        // But backend has to be compatible with older versions of the app.
        versionName = "1.1.1"

        // Version name suffix is appended to the version name to identify the build.
        // Use - to form a legal name for git tag.
        versionNameSuffix = "-$gitCommitId"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        
        // Google OAuth client ID
        // TODO: This is the same now for debug and release builds for convenience.
        // Create a new client ID for debug build, but keep the production one for backward compatibility.
        // https://github.com/NascentCore/inty-backend/issues/171
        buildConfigField("String", "WEB_CLIENT_ID", "\"1034291688895-0e5hq72pghd4nihhpmf989ptv0ag1542.apps.googleusercontent.com\"")

        // 数据安全声明 - 不使用广告ID
        // TODO：这个没有被用到，也不影响实际的构建；应该移除。
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
        create("release") {
            storeFile = rootProject.file(requireProperty(keystoreProperties, "storeFile"))
            storePassword = requireProperty(keystoreProperties, "storePassword")
            keyAlias = requireProperty(keystoreProperties, "release.keyAlias")
            keyPassword = requireProperty(keystoreProperties, "release.keyPassword")
        }
        create("dev") {
            storeFile = rootProject.file(requireProperty(keystoreProperties, "storeFile"))
            storePassword = requireProperty(keystoreProperties, "storePassword")
            keyAlias = requireProperty(keystoreProperties, "dev.keyAlias")
            keyPassword = requireProperty(keystoreProperties, "dev.keyPassword")
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
                // https://developer.android.com/build/include-native-symbols
                debugSymbolLevel = "FULL"
            }
        }
        create("playdebug") {
            // This build is meant to be pushed to Google Play for debugging.
            // It talks to the dev backend, but app is built as release.
            initWith(getByName("release"))

            versionNameSuffix = "-playdebug"
        }
        // TODO: Consider rename this to staging, meaning it's talking to the staging backend,
        // which is not local.
        debug {
            // This build talks to the staging backend.
            // WEB_CLIENT_ID 与 release 签名配置一致，因此必须使用 release 签名配置。
            // 虽然 keystore.properties debug release 签名配置都有，但是 AGP 自己会生成默认的
            // debug signingconfig，因此 keystore.properties 中 debug 签名配置无效。
            signingConfig = signingConfigs.getByName("dev")

            // TODO: Use a different web client ID for debug builds.
            // buildConfigField("String", "WEB_CLIENT_ID", "\"debug_client_id_here\"")

            versionNameSuffix = "-debug"
        }
        create("local") {
            initWith(getByName("debug"))
            versionNameSuffix = "-local"
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
    // ===== AndroidX 核心库 =====
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)

    // ===== Compose UI =====
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.material)

    // ===== 测试库 =====
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)

    // ===== 路由 =====
    implementation(libs.router)
    ksp(libs.therouter.apt)

    // ===== 项目模块 =====
    implementation(project(":utils"))
    implementation(project(":network"))

    // ===== 调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.library.no.op)
    "playdebugImplementation"(libs.chucker.library.no.op)

    // ===== 网络库 =====
    api(libs.retrofit.core)
    implementation(libs.retrofit2.kotlin.coroutines.adapter)

    // ===== 图片加载 =====
    implementation(libs.bundles.coils3)

    // ===== Google 服务 =====
    implementation(libs.billing.ktx)
    implementation(platform(libs.firebase.bom))
    implementation(libs.bundles.firebase.core)
    implementation(libs.bundles.credentials)

    // ===== 图片处理 =====
    api(libs.ucrop)

    // ===== 协程 =====
    implementation(libs.bundles.coroutines)
}
