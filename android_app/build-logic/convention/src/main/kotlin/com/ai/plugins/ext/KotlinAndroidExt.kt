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

/** 扩展一些Project相关的函数定义，便于统一封装gradle的相关android配置 */

/** 配置一下kotlin编译Android的基本模块参数 */
internal fun Project.configureKotlinAndroid(
    commonExtension: CommonExtension<*, *, *, *, *, *>,
) {
  commonExtension.apply {
    compileSdk = ProjectConfig.compileVersion

    defaultConfig { minSdk = ProjectConfig.minSdkVersion }

    compileOptions {
      // Up to Java 11 APIs are available through desugaring
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
    // 通过使用desugar库，可以在高版本的jdk上编译，适配低版本jdk运行
    // Up to Java 11 APIs are available through desugaring
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

/** Configure base Kotlin options 这里配置的jvmTarget只是作用域plugin的生成编译环境，而不会干涉使用plugin的项目配置的jvm编译版本 */
private fun Project.configureKotlin() {
  // Use withType to workaround https://youtrack.jetbrains.com/issue/KT-55947
  tasks.withType<KotlinCompile>().configureEach {
    compilerOptions {
      jvmTarget.assign(JvmTarget.JVM_21)
      // Treat all Kotlin warnings as errors (disabled by default)
      // Override by setting warningsAsErrors=true in your ~/.gradle/gradle.properties
      val warningsAsErrors: String? by project
      allWarningsAsErrors = warningsAsErrors.toBoolean()
      freeCompilerArgs.assign(
          listOf(
              "-opt-in=kotlin.RequiresOptIn",
              // Enable experimental coroutines APIs, including Flow
              "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi",
              "-opt-in=kotlinx.coroutines.FlowPreview",
          )
      )
    }
  }
}

/**
 * 用于优化编译，禁用一些不必要的test的构建 Disable unnecessary Android instrumented tests for the [project] if there
 * is no `androidTest` folder. Otherwise, these projects would be compiled, packaged, installed and
 * ran only to end-up with the following message:
 * > Starting 0 tests on AVD
 *
 * Note: this could be improved by checking other potential sourceSets based on buildTypes and
 * flavors.
 */
internal fun LibraryAndroidComponentsExtension.disableUnnecessaryAndroidTests(
    project: Project,
) = beforeVariants {
  it.androidTest.enable =
      it.androidTest.enable && project.projectDir.resolve("src/androidTest").exists()
}
