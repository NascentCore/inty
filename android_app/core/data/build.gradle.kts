plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.ksp)
    alias(libs.plugins.room)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.kotlin.parcelize)
    alias(libs.plugins.ai.maven.publish)
}

android {
    namespace = "ai.sxwl.android.data"
    // room插件 配置scheme目录
    room { schemaDirectory("$projectDir/schemas") }

    testOptions {
        unitTests {
            isReturnDefaultValues = true
            // 抑制 MockK (ByteBuddy) 动态加载 agent 的警告
            // MockK 使用 ByteBuddy 进行字节码操作，需要动态加载 Java agent
            all {
                it.jvmArgs = (it.jvmArgs ?: emptyList()) + "-XX:+EnableDynamicAgentLoading"
            }
        }
    }

    packaging {
        resources {
            // 解决 META-INF 文件冲突问题
            //
            // 问题原因：
            // 多个依赖库（特别是 Apache HTTP Components 相关库，如 httpclient5、httpcore5、httpcore5-h2）
            // 都在其 JAR 文件中包含了相同的 META-INF 文件（LICENSE、NOTICE、DEPENDENCIES 等）。
            // 当 Android Gradle Plugin 合并这些资源时，会遇到重复文件错误：
            // "3 files found with path 'META-INF/DEPENDENCIES' from inputs"
            //
            // 解决方案：
            // 排除这些 META-INF 文件，因为：
            // 1. 这些文件仅用于声明许可证和依赖信息，不影响运行时功能
            // 2. 多个库使用相同的许可证（Apache 2.0、LGPL 2.1），内容基本相同
            // 3. 排除后可以正常构建，不会影响应用功能
            //
            // 参考：https://developer.android.com/reference/tools/gradle-api/com/android/build/api/dsl/Packaging
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            excludes += "/META-INF/DEPENDENCIES"
            excludes += "/META-INF/LICENSE"
            excludes += "/META-INF/LICENSE.txt"
            excludes += "/META-INF/NOTICE"
            excludes += "/META-INF/NOTICE.txt"
        }
    }

    publishing {
        listOf("debug", "local", "playdebug", "release").forEach { variant ->
            singleVariant(variant) {
                withSourcesJar()
                withJavadocJar()
            }
        }
    }
}

dependencies {

    // ===== Inty SDK（Stainless https://app.stainless.com/ 根据 app/openapi.json 生成的代码）=====
    // 注意：版本必须与 app/build.gradle.kts 保持一致，统一在 libs.versions.toml 中管理
    implementation(libs.inty.kotlin)

    implementation(libs.androidx.dataStore.preferences)
    implementation(libs.mmkv)

    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    implementation(libs.androidx.paging.compose)

    implementation(projects.core.firebase)
    api(libs.billing.client)

    implementation(projects.library.utils)
    implementation(projects.library.network)

    // ===== 网络调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.no.op)
    "playdebugImplementation"(libs.chucker.no.op)

    // ===== Retrofit 协程支持 =====
    implementation(libs.retrofit2.kotlin.coroutines.adapter)

    // ===== 测试依赖 =====
    testImplementation(libs.mockk)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.androidx.test.core)
    testImplementation(libs.robolectric)

    // ===== 日志库（不依赖 Android 环境）=====
    implementation(libs.kotlin.logging)
    implementation(libs.slf4j.api)
    // 在测试环境中使用 slf4j-simple（轻量级实现）
    testImplementation(libs.slf4j.simple)
}
