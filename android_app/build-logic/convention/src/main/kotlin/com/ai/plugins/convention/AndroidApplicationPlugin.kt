package com.ai.plugins.convention

import com.ai.plugins.ext.commonAppConfig
import com.ai.plugins.ext.configureKotlinAndroid
import com.ai.plugins.ext.otherConfiguration
import com.ai.plugins.ext.testDependencies
import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.variant.ApplicationAndroidComponentsExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure

/** 自定义的 gradle 插件，自定义应用程序级别配置，用于复用一些通用可 */
class AndroidApplicationPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            with(pluginManager) {
                apply("com.android.application")
                apply("org.jetbrains.kotlin.android")
            }

            extensions.configure<ApplicationExtension> {
                configureKotlinAndroid(this)
                commonAppConfig(target)
// 配置GradleManagedDevices(this)
            }
            extensions.configure<ApplicationAndroidComponentsExtension> {
// 配置PrintApksTask(this)
            }
//应用程序构建。gradle需要的其他配置
            otherConfiguration()
            testDependencies()
        }
    }
}
