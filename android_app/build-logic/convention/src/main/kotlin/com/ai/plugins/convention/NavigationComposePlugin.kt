package com.ai.plugins.convention

import com.ai.plugins.ext.libs
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.dependencies

/** 简单封装使用compose navigation的配置，需要依赖库和插件 */
class NavigationComposePlugin : Plugin<Project> {

  override fun apply(target: Project) {
    with(target) {
      pluginManager.apply {
        //                apply("org.jetbrains.kotlin.plugin.serialization")
      }
      dependencies {
        add("implementation", libs.findLibrary("androidx.navigation.compose").get())
        add("implementation", libs.findLibrary("kotlinx.serialization.json").get())
      }
    }
  }
}
