plugins {
    alias(libs.plugins.ai.android.library)
    alias(libs.plugins.ksp)
    alias(libs.plugins.room)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.kotlin.parcelize)
    alias(libs.plugins.ai.maven.publish)
}

android {
    namespace = "ai.sxwl.android.data"
    // room插件 配置scheme目录
    room { schemaDirectory("$projectDir/schemas") }
}

dependencies {

    // ===== Inty SDK（Stainless https://app.stainless.com/ 根据 app/openapi.json 生成的代码）=====
    // 使用本地 library/inty_sdk 的版本，避免动态版本在测试时的依赖解析问题
    implementation("com.inty.api:inty-kotlin:0.16.1")

    implementation(libs.androidx.dataStore.preferences)
    implementation(libs.mmkv)

    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    implementation(libs.androidx.paging.compose)

    implementation(projects.core.firebase)
    api(libs.billing.client)

    implementation(projects.library.utils)
    implementation(projects.library.network)

    // ===== 网络调试工具 =====
    debugImplementation(libs.chucker.library)
    "localImplementation"(libs.chucker.library)
    releaseImplementation(libs.chucker.no.op)
    "playdebugImplementation"(libs.chucker.no.op)

    // ===== Retrofit 协程支持 =====
    implementation(libs.retrofit2.kotlin.coroutines.adapter)
}
