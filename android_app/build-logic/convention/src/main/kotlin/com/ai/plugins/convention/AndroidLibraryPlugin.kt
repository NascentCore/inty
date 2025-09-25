package com.ai.plugins.convention

import com.ai.plugins.ext.commonLibConfig
import com.ai.plugins.ext.configureKotlinAndroid
import com.ai.plugins.ext.disableUnnecessaryAndroidTests
import com.ai.plugins.ext.testDependencies
import com.android.build.api.variant.LibraryAndroidComponentsExtension
import com.android.build.gradle.LibraryExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure

/** 用于Android普通module的plugin定义 */
class AndroidLibraryPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            with(pluginManager) {
                apply("com.android.library")
                apply("org.jetbrains.kotlin.android")
            }

            extensions.configure<LibraryExtension> {
                configureKotlinAndroid(this)
                commonLibConfig()
                //                configureGradleManagedDevices(this)
            }
            extensions.configure<LibraryAndroidComponentsExtension> {
                //                configurePrintApksTask(this)
                disableUnnecessaryAndroidTests(target)
            }

            testDependencies()
        }
    }
}
