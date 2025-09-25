import org.gradle.kotlin.dsl.gradlePlugin
import org.gradle.kotlin.dsl.java
import org.gradle.kotlin.dsl.`kotlin-dsl`
import org.gradle.kotlin.dsl.libs
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins { `kotlin-dsl` }

group = "com.ai.buildlogic"

// 作用于build-logic，与项目构建的配置无关
java {
  sourceCompatibility = JavaVersion.VERSION_21
  targetCompatibility = JavaVersion.VERSION_21
}

tasks.withType<KotlinCompile>().configureEach {
  compilerOptions { jvmTarget.assign(JvmTarget.JVM_21) }
}

dependencies {
  compileOnly(libs.android.gradlePlugin)
  compileOnly(libs.kotlin.gradlePlugin)
  compileOnly(libs.ksp.gradlePlugin)
  compileOnly(libs.gson)
}

gradlePlugin {
  plugins {
    // register中 name和id都不能重复
    register("androidApplication") {
      id = libs.plugins.ai.android.application.asProvider().get().pluginId
      // 注意⚠️，这里要使用实现类的全名，便于找到，如果直接在src/main/kotlin下，不属于其他package，则可以直接使用类名
      implementationClass = "com.ai.plugins.convention.AndroidApplicationPlugin"
    }
    register("androidApplicationCompose") {
      id = libs.plugins.ai.android.application.compose.get().pluginId
      implementationClass = "com.ai.plugins.convention.AndroidApplicationComposePlugin"
    }
    register("androidLibrary") {
      id = libs.plugins.ai.android.library.asProvider().get().pluginId
      implementationClass = "com.ai.plugins.convention.AndroidLibraryPlugin"
    }
    register("androidLibraryCompose") {
      id = libs.plugins.ai.android.library.compose.get().pluginId
      implementationClass = "com.ai.plugins.convention.AndroidLibraryComposePlugin"
    }
    register("androidApplicationFlavor") {
      id = libs.plugins.ai.android.application.flavor.get().pluginId
      implementationClass = "com.ai.plugins.convention.AndroidApplicationFlavorPlugin"
    }
    register("jvmLibrary") {
      id = libs.plugins.ai.jvm.library.get().pluginId
      implementationClass = "com.ai.plugins.convention.JvmLibraryPlugin"
    }
    register("mavenPublish") {
      id = libs.plugins.ai.maven.publish.get().pluginId
      implementationClass = "com.ai.plugins.convention.MavenPublishPlugin"
    }
    register("androidFeature") {
      id = libs.plugins.ai.android.feature.asProvider().get().pluginId
      implementationClass = "com.ai.plugins.convention.AndroidFeaturePlugin"
    }
    register("androidFeatureCompose") {
      id = libs.plugins.ai.android.feature.compose.get().pluginId
      implementationClass = "com.ai.plugins.convention.AndroidFeatureComposePlugin"
    }
    register("navigationCompose") {
      id = libs.plugins.ai.android.navigation.compose.get().pluginId
      implementationClass = "com.ai.plugins.convention.NavigationComposePlugin"
    }
  }
}
