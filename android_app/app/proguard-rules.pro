# ===========================================
# Inty Android App R8 混淆规则配置
# 适用于 Release 构建，确保应用稳定运行
# ===========================================

# ===========================================
# 基础配置
# ===========================================

# 保留注解信息
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable
-keepattributes Signature
-keepattributes Exceptions
-keepattributes InnerClasses
-keepattributes EnclosingMethod

# 保留原生方法
-keep class * {
    native <methods>;
}

# 保留 Parcelable 实现
-keep class * implements android.os.Parcelable {
    public static final android.os.Parcelable$Creator *;
}

# ===========================================
# 应用核心类保护
# ===========================================

# 保留应用主包下的所有类
-keep class com.ai.intellimate.** { *; }

# 保留所有Activity
-keep class * extends android.app.Activity { *; }
-keep class * extends androidx.activity.ComponentActivity { *; }

# 保留所有Fragment
-keep class * extends androidx.fragment.app.Fragment { *; }

# 保留所有ViewModel
-keep class * extends androidx.lifecycle.ViewModel { *; }
-keep class * extends ai.sxwl.android.common.base.BaseVM { *; }

# 保留所有Application
-keep class * extends android.app.Application { *; }

# 保留所有Service
-keep class * extends android.app.Service { *; }

# 保留所有BroadcastReceiver
-keep class * extends android.content.BroadcastReceiver { *; }

# 保留所有ContentProvider
-keep class * extends android.content.ContentProvider { *; }

# ===========================================
# 数据模型保护
# ===========================================

# 保留所有数据模型类
-keep class ai.sxwl.android.data.api.model.** { *; }
-keep class ai.sxwl.android.data.billing.** { *; }
-keep class ai.sxwl.android.data.store.** { *; }

# 保留所有Bean类
-keep class com.ai.intellimate.beans.** { *; }

# 保留所有Parcelable数据类（已在基础配置中定义）

# ===========================================
# 序列化框架保护
# ===========================================

# Moshi 序列化保护
-keep class com.squareup.moshi.** { *; }
-keep class * extends com.squareup.moshi.JsonAdapter {
    public static com.squareup.moshi.JsonAdapter create();
}
-keepclassmembers class * {
    @com.squareup.moshi.* <methods>;
    @com.squareup.moshi.* <fields>;
}

# Jackson 序列化保护
-keep class com.fasterxml.jackson.** { *; }
-keep class * extends com.fasterxml.jackson.databind.ser.std.StdSerializer { *; }
-keep class * extends com.fasterxml.jackson.databind.deser.std.StdDeserializer { *; }
-keep class com.fasterxml.jackson.databind.ser.std.NullSerializer { *; }
-keepclassmembers class * {
    @com.fasterxml.jackson.annotation.* <methods>;
    @com.fasterxml.jackson.annotation.* <fields>;
}

# Kotlin序列化保护
-keep class kotlinx.serialization.** { *; }
-keepclassmembers class * {
    @kotlinx.serialization.* <methods>;
    @kotlinx.serialization.* <fields>;
}

# ===========================================
# 网络框架保护
# ===========================================

# Retrofit 保护
-keep class retrofit2.** { *; }
-keepclassmembers class * {
    @retrofit2.http.* <methods>;
}
-dontwarn retrofit2.**

# OkHttp 保护
-keep class okhttp3.** { *; }
-keep class okio.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**

# 自定义网络库保护
-keep class com.architecture.httplib.** { *; }

# ===========================================
# Kotlin 相关保护
# ===========================================

# Kotlin反射
-keep class kotlin.reflect.** { *; }
-keep class kotlin.Metadata { *; }

# Kotlin协程
-keep class kotlinx.coroutines.** { *; }
-keep class kotlinx.coroutines.flow.** { *; }

# ===========================================
# Jetpack Compose 保护
# ===========================================

# Compose 核心
-keep class androidx.compose.** { *; }
-keepclassmembers class androidx.compose.** {
    *;
}

# Compose 预览
-keep class androidx.compose.ui.tooling.preview.** { *; }

# Compose 动画
-keep class androidx.compose.animation.** { *; }

# Compose 导航
-keep class androidx.navigation.** { *; }

# Compose 材质设计
-keep class androidx.compose.material3.** { *; }
-keep class androidx.compose.material.** { *; }

# ===========================================
# Firebase 保护
# ===========================================

# Firebase 核心
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }

# Firebase Analytics
-keep class com.google.firebase.analytics.** { *; }

# Firebase Crashlytics
-keep class com.google.firebase.crashlytics.** { *; }

# Firebase Performance
-keep class com.google.firebase.perf.** { *; }

# ===========================================
# 第三方库保护
# ===========================================

# MMKV 存储
-keep class com.tencent.mmkv.** { *; }

# Coil 图片加载
-keep class coil.** { *; }
-keep class coil3.** { *; }

# Media3 音视频
-keep class androidx.media3.** { *; }

# CameraX
-keep class androidx.camera.** { *; }

# Koin 依赖注入
-keep class org.koin.** { *; }
-keep class org.koin.core.** { *; }

# ===========================================
# inty-sdk 保护
# ===========================================

# inty-sdk 核心API
-keep class com.inty.api.** { *; }

# inty-sdk 模型类
-keep class com.inty.api.models.** { *; }

# inty-sdk 服务类
-keep class com.inty.api.services.** { *; }

# ===========================================
# 日志和调试
# ===========================================

# 保留日志库
-keep class com.tencent.mars.xlog.** { *; }

# ===========================================
# 警告抑制
# ===========================================

# 抑制常见警告
-dontwarn java.lang.management.ManagementFactory
-dontwarn java.lang.management.RuntimeMXBean
-dontwarn java.lang.management.**
-dontwarn java.beans.ConstructorProperties
-dontwarn java.beans.Transient
-dontwarn org.brotli.dec.BrotliInputStream
-dontwarn org.ietf.jgss.GSSContext
-dontwarn org.ietf.jgss.GSSCredential
-dontwarn org.ietf.jgss.GSSException
-dontwarn org.ietf.jgss.GSSManager
-dontwarn org.ietf.jgss.GSSName
-dontwarn org.ietf.jgss.Oid
-dontwarn javax.annotation.**
-dontwarn javax.inject.**
-dontwarn javax.xml.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**
-dontwarn java.lang.invoke.StringConcatFactory

# Ktor 相关警告
-dontwarn io.ktor.**
-keep class io.ktor.** { *; }

# ===========================================
# 性能优化
# ===========================================

# 不混淆枚举
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# 不混淆Serializable
-keepclassmembers class * implements java.io.Serializable {
    static final long serialVersionUID;
    private static final java.io.ObjectStreamField[] serialPersistentFields;
    private void writeObject(java.io.ObjectOutputStream);
    private void readObject(java.io.ObjectInputStream);
    java.lang.Object writeReplace();
    java.lang.Object readResolve();
}

# ===========================================
# 特殊保护
# ===========================================

# 保留所有Companion对象
-keepclassmembers class * {
    public static ** Companion;
}

# 保留所有伴生对象
-keepclassmembers class * {
    public static ** Companion;
    public static ** INSTANCE;
}

# 保留所有内部类
-keepclassmembers class * {
    public static class *;
}

# ===========================================
# 测试相关（Release构建时会被移除）
# ===========================================

# 保留测试相关类（仅在debug构建中）
-keep class * extends junit.framework.TestCase { *; }
-keep class org.junit.** { *; }
-keep class org.mockito.** { *; }
