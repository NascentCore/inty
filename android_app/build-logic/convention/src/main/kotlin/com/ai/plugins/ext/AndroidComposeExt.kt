package com.ai.plugins.ext

import com.android.build.api.dsl.CommonExtension
import org.gradle.api.Project
import org.gradle.kotlin.dsl.dependencies
import org.gradle.kotlin.dsl.withType
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

/** 定义一些可用于Android端 compose项目的配置gradle的扩展函数 */

/** Configure Compose-specific options */
internal fun Project.configureAndroidCompose(commonExtension: CommonExtension<*, *, *, *, *, *>) {
    commonExtension.apply {
        buildFeatures { compose = true }

        dependencies {
            val bom = libs.findLibrary("androidx.compose-bom").get()
            // 注意⚠️，这里的findLibrary要在libs.version.toml中有的才可以,最好名称中-或_要替换为. 如activity-compose 使用如下。
            add("implementation", libs.findLibrary("androidx.activity.compose").get())
            add("implementation", platform(bom))
            add("implementation", libs.findLibrary("androidx.compose-ui").get())
            add("implementation", libs.findLibrary("androidx.compose-ui.graphics").get())
            add("implementation", libs.findLibrary("androidx.compose-ui.tooling").get())
            add("implementation", libs.findLibrary("androidx.compose-ui.tooling.preview").get())
            add("implementation", libs.findLibrary("androidx.compose-material3").get())

            add("androidTestImplementation", platform(bom))
            add(
                "androidTestImplementation",
                libs.findLibrary("androidx.compose-ui.test.junit4").get(),
            )
            add("debugImplementation", libs.findLibrary("androidx.compose-ui.tooling").get())
            // Add ComponentActivity to debug manifest
            add("debugImplementation", libs.findLibrary("androidx.compose-ui-test-manifest").get())
        }

        testOptions {
            unitTests {
                // For Robolectric
                isIncludeAndroidResources = true
            }
        }
    }

    tasks.withType<KotlinCompile>().configureEach {
        compilerOptions { freeCompilerArgs.addAll(buildComposeMetricsParameters()) }
    }
}

private fun Project.buildComposeMetricsParameters(): List<String> {
    val metricParameters = mutableListOf<String>()
    val enableMetricsProvider = project.providers.gradleProperty("enableComposeCompilerMetrics")
    val relativePath = projectDir.relativeTo(rootDir)

    val enableMetrics = (enableMetricsProvider.orNull == "true")
    if (enableMetrics) {
        val metricsFolder =
            rootProject.layout.buildDirectory.asFile
                .get()
                .resolve("compose-metrics")
                .resolve(relativePath)
        metricParameters.add("-P")
        metricParameters.add(
            "plugin:androidx.compose.compiler.plugins.kotlin:metricsDestination=" +
                metricsFolder.absolutePath
        )
    }

    val enableReportsProvider = project.providers.gradleProperty("enableComposeCompilerReports")
    val enableReports = (enableReportsProvider.orNull == "true")
    if (enableReports) {
        val reportsFolder =
            rootProject.layout.buildDirectory.asFile
                .get()
                .resolve("compose-reports")
                .resolve(relativePath)
        metricParameters.add("-P")
        metricParameters.add(
            "plugin:androidx.compose.compiler.plugins.kotlin:reportsDestination=" +
                reportsFolder.absolutePath
        )
    }
    return metricParameters.toList()
}
