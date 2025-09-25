package com.ai.plugins.convention

import com.ai.plugins.ext.configureKotlinJvm
import org.gradle.api.Plugin
import org.gradle.api.Project

/**
 * 用于jvm编译module的plugin定义
 */
class JvmLibraryPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            with(pluginManager) {
                apply("org.jetbrains.kotlin.jvm")
                apply("java-library")
            }
            configureKotlinJvm()
        }
    }
}
