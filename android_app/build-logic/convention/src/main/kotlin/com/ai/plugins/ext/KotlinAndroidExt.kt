package com.ai.plugins.ext

import com.ai.plugins.ProjectConfig
import com.android.build.api.dsl.CommonExtension
import com.android.build.api.variant.LibraryAndroidComponentsExtension
import org.gradle.api.JavaVersion
import org.gradle.api.Project
import org.gradle.api.plugins.JavaPluginExtension
import org.gradle.kotlin.dsl.assign
import org.gradle.kotlin.dsl.configure
import org.gradle.kotlin.dsl.dependencies
import org.gradle.kotlin.dsl.kotlin
import org.gradle.kotlin.dsl.provideDelegate
import org.gradle.kotlin.dsl.withType
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

/** 扩展一些Project相关的函数定义，统一封装gradle的相关android配置 */

/** 配置一下kotlin编译Android的基本模块参数 */
internal fun Project.configureKotlinAndroid(commonExtension: CommonExtension<*, *, *, *, *, *>) {
    commonExtension.apply {
        compileSdk = ProjectConfig.compileVersion

        defaultConfig { minSdk = ProjectConfig.minSdkVersion }

        compileOptions {
// 通过脱糖最多可使用 Java 11 API
// https://developer.android.com/studio/write/java11-minimal-support-table
            sourceCompatibility = JavaVersion.VERSION_21
            targetCompatibility = JavaVersion.VERSION_21
            isCoreLibraryDesugaringEnabled = true
        }
    }

    configureKotlin()

    dependencies {
        add("coreLibraryDesugaring", libs.findLibrary("android.desugarJdkLibs").get())
        add("testImplementation", kotlin("test"))
        add("androidTestImplementation", kotlin("test"))

        add("implementation", libs.findLibrary("kotlin.stdlib").get())

        add("implementation", libs.findLibrary("kotlinx.coroutines.android").get())
        add("implementation", libs.findLibrary("kotlinx.coroutines.core").get())
        add("testImplementation", libs.findLibrary("kotlinx.coroutines.test").get())

        add("implementation", libs.findLibrary("kotlinx.serialization.json").get())
        add("implementation", libs.findLibrary("kotlinx.datetime").get())
    }
}

/** 配置一下kotlin的非Android项目，jvm平台的基础配置 */
internal fun Project.configureKotlinJvm() {
    extensions.configure<JavaPluginExtension> {
// 通过使用desugar库，可以在高版本的jdk上编译，支持低版本jdk运行
// 通过脱糖最多可使用 Java 11 API
// https://developer.android.com/studio/write/java11-minimal-support-table
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    configureKotlin()

    dependencies {
        add("testImplementation", kotlin("test"))

        add("implementation", libs.findLibrary("kotlin.stdlib").get())

        add("implementation", libs.findLibrary("kotlinx.coroutines.core").get())
        add("testImplementation", libs.findLibrary("kotlinx.coroutines.test").get())

        add("implementation", libs.findLibrary("kotlinx.serialization.json").get())
        add("implementation", libs.findLibrary("kotlinx.datetime").get())
    }
}

/** 选项配置基本 Kotlin 这里配置的jvmTarget只是作用域插件的生成编译环境，而不会干扰使用插件的项目配置的jvm编译版本 */
private fun Project.configureKotlin() {
// 使用 withType 解决方法 https://youtrack.jetbrains.com/issue/KT-55947
    tasks.withType<KotlinCompile>().configureEach {
        compilerOptions {
            jvmTarget.assign(JvmTarget.JVM_21)
// 将所有 Kotlin 警告视为错误（默认禁用）
// 通过在 ~/.gradle/gradle 中设置 warningsAsErrors=true 进行覆盖。pr操作
            val warningsAsErrors: String? by project
            allWarningsAsErrors = warningsAsErrors.toBoolean()
            freeCompilerArgs.assign(
                listOf(
                    "-opt-in=kotlin.RequiresOptIn",
// 实现实验工程良好APIs，包括Flow
                    "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi",
                    "-opt-in=kotlinx.coroutines.FlowPreview",
                )
            )
        }
    }
}

/**
 *对于优化编译，禁止一些不必要的测试的构建禁止不必要的Android仪器测试[project]如果有
 * 没有 `androidTest` 文件夹。否则，这些 projects 将被编译、压缩、安装并
 * 只运行到最后显示以下消息：
 * > 在 AVD 上开始 0 次测试
 *
 *注意：这可能是 improved 通过基于 buildTypes 的其他潜在来源集并进行检查
 *口味。*/
internal fun LibraryAndroidComponentsExtension.disableUnnecessaryAndroidTests(project: Project) =
    beforeVariants {
        it.androidTest.enable =
            it.androidTest.enable && project.projectDir.resolve("src/androidTest").exists()
    }
