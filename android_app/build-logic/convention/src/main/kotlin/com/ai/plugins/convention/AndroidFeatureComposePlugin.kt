package com.ai.plugins.convention

import com.ai.plugins.ext.configureAndroidCompose
import com.ai.plugins.ext.configureKotlinAndroid
import com.ai.plugins.ext.libs
import com.ai.plugins.ext.testDependencies
import com.android.build.api.dsl.DynamicFeatureExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure
import org.gradle.kotlin.dsl.dependencies
import org.gradle.kotlin.dsl.getByType
import org.gradle.kotlin.dsl.project

/** 用于Android 动态模块的plugin定义,包含compose的依赖配置 */
class AndroidFeatureComposePlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("com.android.dynamic-feature")
            pluginManager.apply("org.jetbrains.kotlin.android")
            pluginManager.apply("org.jetbrains.kotlin.plugin.compose")

            extensions.configure<DynamicFeatureExtension> { configureKotlinAndroid(this) }

            testDependencies()

            val extension = extensions.getByType<DynamicFeatureExtension>()
            configureAndroidCompose(extension)

            dependencies {
                add("implementation", project(":app"))
                add("implementation", libs.findLibrary("androidx.core.ktx").get())

                add("androidTestImplementation", libs.findLibrary("androidx.annotation").get())
            }
        }
    }
}
