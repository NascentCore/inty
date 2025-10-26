package com.ai.plugins.convention

import com.ai.plugins.ext.libs
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.dependencies

/** 简单封装使用compose导航的配置，需要依赖库和插件 */
class NavigationComposePlugin : Plugin<Project> {

    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply {
// 应用("org.jetbrains.kotlin.plugin.序列化”）
            }
            dependencies {
                add("implementation", libs.findLibrary("androidx.navigation.compose").get())
                add("implementation", libs.findLibrary("kotlinx.serialization.json").get())
            }
        }
    }
}
