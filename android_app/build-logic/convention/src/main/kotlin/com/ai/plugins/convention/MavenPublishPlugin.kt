package com.ai.plugins.convention

import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.publish.PublishingExtension
import org.gradle.api.publish.maven.MavenPublication
import org.gradle.kotlin.dsl.configure

/** 用于配置module 打包jar，aar的一些插件属性等 */
class MavenPublishPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("maven-publish")
            afterEvaluate {
                // 配置gradle中对应publishing闭包的设置
                extensions.configure<PublishingExtension>() {
                    publications {
                        // 也就是代码构建类型，jvm的打包有java和kotlin两个默认来源
                        // aar的打包，一般默认debug和release两个，
                        components.forEach {
                            create(it.name, MavenPublication::class.java) {
                                groupId = project.group.toString()
                                // 为了避免java与kotlin，release与debug重复构建打包时候的覆盖，这里区分一下
                                artifactId = project.name + it.name
                                version = project.version.toString()

                                from(it)
                            }
                        }
                    }

                    repositories {
                        mavenLocal()
                        val pkgUrl =
                            findProperty("gpr.package.url") as String?
                                ?: System.getenv("GITHUB_PACKAGES_URL")
                        val gprUser = findProperty("gpr.user") as String?
                        val gprKey = findProperty("gpr.key") as String?
                        val actor = System.getenv("GITHUB_ACTOR")
                        val token = System.getenv("GITHUB_TOKEN")
                        val user = gprUser ?: actor
                        val password = gprKey ?: token
                        if (!pkgUrl.isNullOrBlank() && !user.isNullOrBlank() && !password.isNullOrBlank()) {
                            maven {
                                name = "GitHubPackages"
                                url = uri(pkgUrl)
                                credentials {
                                    username = user
                                    this.password = password
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
