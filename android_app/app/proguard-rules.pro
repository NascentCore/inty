# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# 保留注解信息
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable
-keepattributes Signature
-keepattributes Exceptions

# 保留原生方法
-keep class * {
    native <methods>;
}

# 保留 Parcelable 实现
-keep class * implements android.os.Parcelable {
  public static final android.os.Parcelable$Creator *;
}

# 保留应用数据模型
-keep class com.ai.inty.beans.** {
    public *;
}

# 保留计费相关类
-keep class com.ai.inty.billing.** {
    public *;
}
-keep class ai.sxwl.android.data.billing.VipStatus { *; }
-keep class ai.sxwl.android.data.billing.VipPlan { *; }
-keep class ai.sxwl.android.data.billing.BillingEvent { *; }

# 保留日志库
-keep class com.tencent.mars.xlog.** { *; }

# Retrofit 混淆规则
-keepattributes Signature
-keepattributes Exceptions
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}

# Moshi 混淆规则
-keep class com.squareup.moshi.** { *; }
-keep class * extends com.squareup.moshi.JsonAdapter {
    public static com.squareup.moshi.JsonAdapter create();
}

# Jackson 混淆规则
-keep class com.fasterxml.jackson.** { *; }
-keep class * extends com.fasterxml.jackson.databind.ser.std.StdSerializer { *; }
-keep class * extends com.fasterxml.jackson.databind.deser.std.StdDeserializer { *; }
-keep class com.fasterxml.jackson.databind.ser.std.NullSerializer { *; }

# 保留Kotlin反射相关类
-keep class kotlin.reflect.** { *; }
-keep class kotlin.Metadata { *; }

# 保留数据类
-keepclassmembers class * {
    @com.squareup.moshi.* <methods>;
    @com.fasterxml.jackson.annotation.* <methods>;
}

# TheRouter 混淆规则已移除

# Firebase 混淆规则
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }

# Compose 混淆规则
-keep class androidx.compose.** { *; }
-keepclassmembers class androidx.compose.** {
    *;
}

# MMKV 混淆规则
-keep class com.tencent.mmkv.** { *; }

# 保留 Compose 预览相关类
-keep class androidx.compose.ui.tooling.preview.** { *; }

# Ktor 调试检测器相关规则
-dontwarn java.lang.management.ManagementFactory
-dontwarn java.lang.management.RuntimeMXBean
-dontwarn java.lang.management.**

# Ktor 相关规则
-keep class io.ktor.** { *; }
-dontwarn io.ktor.**

# R8 缺失类警告抑制规则
# 这些类在 Android 运行时中不可用，但被某些库引用
-dontwarn java.beans.ConstructorProperties
-dontwarn java.beans.Transient
-dontwarn org.brotli.dec.BrotliInputStream
-dontwarn org.ietf.jgss.GSSContext
-dontwarn org.ietf.jgss.GSSCredential
-dontwarn org.ietf.jgss.GSSException
-dontwarn org.ietf.jgss.GSSManager
-dontwarn org.ietf.jgss.GSSName
-dontwarn org.ietf.jgss.Oid
