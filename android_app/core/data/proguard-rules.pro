# ===========================================
# Core Data Module R8 混淆规则配置
# 核心数据模块专用混淆规则
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

# ===========================================
# 数据模型保护
# ===========================================

# 保留所有数据模型类
-keep class ai.sxwl.android.data.api.model.** { *; }
-keep class ai.sxwl.android.data.billing.** { *; }
-keep class ai.sxwl.android.data.store.** { *; }
-keep class ai.sxwl.android.data.http.** { *; }
-keep class ai.sxwl.android.data.chat.** { *; }
-keep class ai.sxwl.android.data.usecase.** { *; }
-keep class ai.sxwl.android.data.domain.** { *; }
-keep class ai.sxwl.android.data.di.** { *; }

# ===========================================
# API接口保护
# ===========================================

# 保留所有API接口
-keep class ai.sxwl.android.data.api.** { *; }

# 保留网络服务管理器
-keep class ai.sxwl.android.data.api.NetServiceMgr { *; }

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
# 数据存储保护
# ===========================================

# MMKV 存储
-keep class com.tencent.mmkv.** { *; }

# Room 数据库
-keep class androidx.room.** { *; }
-keep class * extends androidx.room.RoomDatabase { *; }

# ===========================================
# 计费相关保护
# ===========================================

# 保留计费相关类
-keep class ai.sxwl.android.data.billing.** { *; }

# 保留计费状态类
-keep class ai.sxwl.android.data.billing.VipStatus { *; }
-keep class ai.sxwl.android.data.billing.VipPlan { *; }
-keep class ai.sxwl.android.data.billing.BillingEvent { *; }

# ===========================================
# 聊天相关保护
# ===========================================

# 保留聊天相关类
-keep class ai.sxwl.android.data.chat.** { *; }

# 保留聊天会话管理器
-keep class ai.sxwl.android.data.chat.ChatSessionManager { *; }

# ===========================================
# 用例相关保护
# ===========================================

# 保留用例相关类
-keep class ai.sxwl.android.data.usecase.** { *; }

# ===========================================
# 领域相关保护
# ===========================================

# 保留领域相关类
-keep class ai.sxwl.android.data.domain.** { *; }

# ===========================================
# 依赖注入保护
# ===========================================

# 保留依赖注入相关类
-keep class ai.sxwl.android.data.di.** { *; }

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
# 警告抑制
# ===========================================

# 抑制常见警告
-dontwarn java.lang.invoke.StringConcatFactory
-dontwarn co.langem.androidutils.tools.LogTools
-dontwarn java.lang.management.**
-dontwarn javax.annotation.**
-dontwarn javax.inject.**
-dontwarn javax.xml.**

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
