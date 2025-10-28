plugins { alias(libs.plugins.ai.android.library) }

android { namespace = "ai.sxwl.android.utils" }

dependencies {
    // ===== AndroidX 核心库 =====
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)

    implementation(libs.androidx.startup)

    // 图片压缩库
    implementation(libs.luban)
}
