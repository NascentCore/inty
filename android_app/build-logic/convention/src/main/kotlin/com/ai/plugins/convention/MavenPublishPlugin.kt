package com.ai.plugins.convention

import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.publish.PublishingExtension
import org.gradle.api.publish.maven.MavenPublication
import org.gradle.kotlin.dsl.configure

/** 用于配置模块备份jar，aar的一些插件属性等 */
class MavenPublishPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("maven-publish")
            afterEvaluate {
// 配置gradle中发布闭包的设置
                extensions.configure<PublishingExtension>() {
                    publications {
// 代码构建类型，jvm的资源有java和kotlin两个默认来源
// aar的资源，一般默认debug和release两个，
                        components.forEach {
                            create(it.name, MavenPublication::class.java) {
                                groupId = project.group.toString()
// 为了避免java与kotlin，release与debug重复构建备份时的覆盖，这里区分一下
                                artifactId = project.name + it.name
                                version = project.version.toString()

                                from(it)
                            }
                        }
                    }

                    repositories { mavenLocal() }
                }
            }
        }
    }
}
