plugins { alias(libs.plugins.ai.android.library) }

android { namespace = "com.inty.utils" }

dependencies {
    // ===== AndroidX 核心库 =====
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)

    // ===== 腾讯系库 =====
    api(libs.mmkv)
    implementation(libs.mars.xlog)
}
