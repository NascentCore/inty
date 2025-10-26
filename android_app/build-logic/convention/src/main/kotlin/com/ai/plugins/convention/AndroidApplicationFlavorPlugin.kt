package com.ai.plugins.convention

import com.ai.plugins.ext.configureFlavors
import com.android.build.api.dsl.ApplicationExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure

/** 用于区分app的差异的定义插件插件 */
class AndroidApplicationFlavorPlugin : Plugin<Project> {

    override fun apply(target: Project) {
        with(target) { extensions.configure<ApplicationExtension> { configureFlavors(this) } }
    }
}
