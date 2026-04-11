plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.kotlin.serialization)
}

android { namespace = "ai.sxwl.android.inty.voicecall" }

dependencies {
    implementation(libs.androidx.annotation)
    implementation(libs.bundles.websockets)
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    compilerOptions { freeCompilerArgs.add("-Xannotation-default-target=param-property") }
}
