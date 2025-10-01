package com.ai.plugins.ext

import org.gradle.api.Project
import org.gradle.api.artifacts.Configuration
import org.gradle.api.artifacts.VersionCatalog
import org.gradle.api.artifacts.VersionCatalogsExtension
import org.gradle.kotlin.dsl.dependencies
import org.gradle.kotlin.dsl.exclude
import org.gradle.kotlin.dsl.getByName
import org.gradle.kotlin.dsl.getByType
import org.gradle.kotlin.dsl.invoke
import org.gradle.kotlin.dsl.kotlin

/** 扩展一些Project相关配置的函数 */

/** 定义libs扩展属性，类似于在build-logic之外，项目使用catalog的toml配置， 在build-logic的对应代码内操作libs方便 */
val Project.libs
    get(): VersionCatalog = extensions.getByType<VersionCatalogsExtension>().named("libs")

internal fun Project.otherConfiguration() {
    // 依赖冲突的处理
    configurations {
        getByName<Configuration>("implementation") {
            // room 2.6.1中compiler依赖了老旧的com.intellij的annotations 12的包，与 org.jetbrains.annotations
            // 23的包冲突了
            exclude(group = "com.intellij", module = "annotations")
        }
    }
}

internal fun Project.testDependencies() {
    dependencies {
        add("testImplementation", kotlin("test"))
        add("androidTestImplementation", kotlin("test"))

        add("testImplementation", libs.findLibrary("turbine").get())
        add("testImplementation", libs.findLibrary("junit").get())
        add("androidTestImplementation", libs.findLibrary("androidx.junit").get())
        add("androidTestImplementation", libs.findLibrary("androidx.espresso.core").get())
    }
}
