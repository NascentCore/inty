plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ai.maven.publish)
}

group = "ai.sxwl.android"

version = "1.0.0"

android {
    namespace = "ai.sxwl.android.inty.voicecall"

    publishing {
        listOf("debug", "local", "playdebug", "release").forEach { variant ->
            singleVariant(variant) {
                withSourcesJar()
                withJavadocJar()
            }
        }
    }
}

dependencies {
    implementation(libs.androidx.annotation)
    implementation(libs.bundles.websockets)
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    compilerOptions { freeCompilerArgs.add("-Xannotation-default-target=param-property") }
}
