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

// 自动递增 versionCode 的函数
fun getVersionCode(): Int {
    // 检查是否在 CI 环境中
    val isCIBuild = System.getenv("CI") != null || System.getenv("GITHUB_ACTIONS") != null
    
    if (isCIBuild) {
        // CI 环境：基于时间戳或提交历史生成版本号
        val gitCommitCount = try {
            val process = ProcessBuilder("git", "rev-list", "--count", "HEAD").start()
            process.waitFor()
            if (process.exitValue() == 0) {
                process.inputStream.bufferedReader().readText().trim().toInt()
            } else {
                // fallback：使用时间戳生成版本号
                (System.currentTimeMillis() / 1000 / 3600).toInt() // 每小时递增
            }
        } catch (e: Exception) {
            println("⚠️ Git commit count failed, using timestamp fallback")
            (System.currentTimeMillis() / 1000 / 3600).toInt()
        }
        
        // 确保 CI 版本号不会太小（至少从10开始）
        val ciVersionCode = maxOf(gitCommitCount, 10)
        println("🤖 CI Build detected! Using version code: $ciVersionCode (based on git commits: $gitCommitCount)")
        return ciVersionCode
    }
    
    // 本地构建：使用原有逻辑
    val versionFile = rootProject.file("version.properties")
    val versionProperties = Properties()
    
    // 如果文件不存在，创建初始版本
    if (!versionFile.exists()) {
        versionProperties.setProperty("versionCode", "1")
        versionFile.outputStream().use { 
            versionProperties.store(it, "Version Code Auto Increment") 
        }
        return 1
    }
    
    // 读取当前版本号
    versionFile.inputStream().use { 
        versionProperties.load(it) 
    }
    
    val currentVersionCode = versionProperties.getProperty("versionCode", "1").toInt()
    
    // 检查是否是 release 构建任务
    val isReleaseBuild = gradle.startParameter.taskNames.any { 
        it.contains("bundle") && it.contains("Release") 
    }
    
    if (isReleaseBuild) {
        // 如果是 release 构建，递增版本号并保存
        val newVersionCode = currentVersionCode + 1
        versionProperties.setProperty("versionCode", newVersionCode.toString())
        versionFile.outputStream().use { 
            versionProperties.store(it, "Version Code Auto Increment - Updated on Release Build") 
        }
        println("🚀 Release build detected! Version code incremented: $currentVersionCode -> $newVersionCode")
        return newVersionCode
    }
    
    return currentVersionCode
}

android {
    namespace = "com.ai.inty"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.ai.intellimate"
        minSdk = 29
        targetSdk = 36
        versionCode = getVersionCode()
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
            versionNameSuffix = " ($gitCommitId)"
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
//    implementation(libs.billing.ktx)
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

// 添加任务来输出版本信息，供GitHub Actions使用
tasks.register("printVersionCode") {
    doLast {
        println(android.defaultConfig.versionCode)
    }
}

tasks.register("printVersionName") {
    doLast {
        println(android.defaultConfig.versionName)
    }
}
