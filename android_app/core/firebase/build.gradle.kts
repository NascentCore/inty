plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.kotlin.android)
}


group = "ai.sxwl.android"
version = "1.0.0"


android {
    namespace = "ai.sxwl.android.firebase"
}

dependencies {

    implementation(libs.androidx.startup)

    // Firebase dependencies
    implementation(platform(libs.firebase.bom))
    implementation(libs.bundles.firebase)

    // Core dependencies
    implementation(projects.library.utils)

}
