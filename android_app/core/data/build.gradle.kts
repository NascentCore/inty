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
    //room插件 配置scheme目录
    room {
        schemaDirectory("$projectDir/schemas")
    }
}

dependencies {

    implementation(libs.androidx.dataStore.preferences)

    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    implementation(projects.core.firebase)
    implementation(libs.billing.client)

    implementation(projects.library.utils)
    implementation(projects.library.network)

}
