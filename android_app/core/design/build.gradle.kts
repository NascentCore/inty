plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.ai.android.library.compose)
    alias(libs.plugins.ai.maven.publish)
}

group = "ai.sxwl.android"

version = "1.0.0"

android { namespace = "ai.sxwl.android.design" }

dependencies {
    api(libs.bundles.coil.bundle)
    api(libs.bundles.compose.ui.bundle)
    api(libs.bundles.compose.jetpack.bundle)

    implementation(libs.androidx.startup)
}
