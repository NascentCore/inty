# ===========================================
# Network Module R8 混淆规则配置
# 网络模块专用混淆规则
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

# 保留Moshi注解
-keep @com.squareup.moshi.JsonQualifier interface * { *; }

# Jackson 序列化保护
-keep class com.fasterxml.jackson.** { *; }
-keep class * extends com.fasterxml.jackson.databind.ser.std.StdSerializer { *; }
-keep class * extends com.fasterxml.jackson.databind.deser.std.StdDeserializer { *; }
-keepclassmembers class * {
    @com.fasterxml.jackson.annotation.* <methods>;
    @com.fasterxml.jackson.annotation.* <fields>;
}

# ===========================================
# Kotlin 相关保护
# ===========================================

# Kotlin反射
-keep class kotlin.reflect.** { *; }
-keep class kotlin.Metadata { *; }

# Kotlin协程
-keep class kotlinx.coroutines.** { *; }

# ===========================================
# 网络相关保护
# ===========================================

# HTTP 相关类
-keep class java.net.** { *; }
-keep class javax.net.** { *; }

# SSL/TLS 相关
-keep class javax.net.ssl.** { *; }
-keep class java.security.** { *; }

# ===========================================
# 警告抑制
# ===========================================

# 抑制网络相关警告
-dontwarn java.lang.management.**
-dontwarn javax.annotation.**
-dontwarn javax.inject.**
-dontwarn javax.xml.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**

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


