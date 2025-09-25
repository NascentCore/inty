package com.ai.plugins.convention

import com.ai.plugins.ext.configureAndroidCompose
import com.android.build.api.dsl.ApplicationExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.getByType

/** 配置一些compose相关的通用设置，定义一个自定义插件 */
class AndroidApplicationComposePlugin : Plugin<Project> {

  override fun apply(target: Project) {
    with(target) {
      pluginManager.apply("com.android.application")
      pluginManager.apply("org.jetbrains.kotlin.plugin.compose")
      // 配置compose
      val extension = extensions.getByType<ApplicationExtension>()
      configureAndroidCompose(extension)
    }
  }
}
