plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.ai.android.library.compose)
    alias(libs.plugins.ai.maven.publish)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ai.android.navigation.compose)
}

group = "ai.sxwl.android"
version = "1.0.0"

android {
    namespace = "ai.sxwl.android.common"
}

dependencies {

    implementation(libs.accompanist.permissions)

    implementation(libs.bundles.compose.ui.bundle)
    implementation(libs.androidx.webkit)

    implementation(projects.core.data)
    implementation(projects.library.utils)

    // Google认证相关依赖
    implementation(libs.bundles.google.auth)

    // Coil图片加载
    implementation(libs.coil.kt)

}
