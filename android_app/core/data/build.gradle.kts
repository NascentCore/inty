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
    api(projects.library.intyVoiceCall)
    implementation(libs.androidx.dataStore.preferences)
    implementation(libs.androidx.dataStore)
    implementation(libs.mmkv)

    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)
    implementation(libs.androidx.room.paging)

    implementation(libs.androidx.paging.compose)
    implementation(libs.androidx.paging.runtime)

    implementation(projects.core.firebase)
    api(libs.billing.client)

    implementation(projects.library.utils)
    implementation(projects.library.network)

    // ===== Moshi 代码生成（用于 @JsonClass(generateAdapter = true)）=====
    // 注意：需要在每个使用 @JsonClass 注解的模块中单独配置 ksp
    ksp(libs.moshi.kotlin.codegen)

    // ===== 网络调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.no.op)
    "playdebugImplementation"(libs.chucker.no.op)

    // ===== Retrofit 协程支持 =====
    implementation(libs.retrofit2.kotlin.coroutines.adapter)

    // ===== 测试依赖 =====
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.androidx.test.core)
    testImplementation(libs.robolectric)

    // ===== 日志库（不依赖 Android 环境）=====
    implementation(libs.kotlin.logging)
    implementation(libs.slf4j.api)
    // 在测试环境中使用 slf4j-simple（轻量级实现）
    testImplementation(libs.slf4j.simple)

    // ===== Websockets =====
    implementation(libs.bundles.websockets)

    // ===== 依赖注入 =====
    implementation(platform(libs.koin.bom))
    implementation(libs.koin.androidx.compose)
    implementation(libs.koin.androidx.navigation)
    testImplementation(libs.koin.test.junit)
    testImplementation(libs.koin.test.android)
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    compilerOptions { freeCompilerArgs.add("-Xannotation-default-target=param-property") }
}
