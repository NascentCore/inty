plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.architecture.httplib"
    compileSdk = 36
}

dependencies {
// ===== 调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.no.op)
    "playdebugImplementation"(libs.chucker.no.op)
// ===== JSON 序列化 =====
    ksp(libs.moshi.kotlin.codegen)
// ===== 项目模块 =====
    implementation(projects.library.utils)
    api(libs.bundles.moshi)
}
