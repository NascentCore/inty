# ===========================================
# Core Common Module R8 混淆规则配置
# 核心通用模块专用混淆规则
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
# 核心通用类保护
# ===========================================

# 保留所有核心通用类
-keep class ai.sxwl.android.common.** { *; }

# 保留所有基础类
-keep class ai.sxwl.android.common.base.** { *; }

# 保留所有分析类
-keep class ai.sxwl.android.common.analytics.** { *; }

# ===========================================
# BaseActivity 保护
# ===========================================

# 保留BaseActivity
-keep class ai.sxwl.android.common.base.BaseActivity { *; }

# 保留BaseVM
-keep class ai.sxwl.android.common.base.BaseVM { *; }

# 保留BaseMVI
-keep class ai.sxwl.android.common.base.BaseMVI { *; }

# ===========================================
# 页面追踪保护
# ===========================================

# 保留页面追踪相关类
-keep class ai.sxwl.android.common.analytics.PageTrackingHelper { *; }

# ===========================================
# Android 系统相关保护
# ===========================================

# 保留Application相关
-keep class * extends android.app.Application { *; }

# 保留Activity相关
-keep class * extends android.app.Activity { *; }
-keep class * extends androidx.activity.ComponentActivity { *; }

# 保留Fragment相关
-keep class * extends androidx.fragment.app.Fragment { *; }

# 保留ViewModel相关
-keep class * extends androidx.lifecycle.ViewModel { *; }

# ===========================================
# 生命周期相关保护
# ===========================================

# 保留生命周期相关类
-keep class androidx.lifecycle.** { *; }

# ===========================================
# 协程相关保护
# ===========================================

# 保留协程相关类
-keep class kotlinx.coroutines.** { *; }
-keep class kotlinx.coroutines.flow.** { *; }

# ===========================================
# 反射相关保护
# ===========================================

# 保留Kotlin反射
-keep class kotlin.reflect.** { *; }
-keep class kotlin.Metadata { *; }

# ===========================================
# 序列化相关保护
# ===========================================

# 保留Kotlin序列化
-keep class kotlinx.serialization.** { *; }
-keepclassmembers class * {
    @kotlinx.serialization.* <methods>;
    @kotlinx.serialization.* <fields>;
}

# ===========================================
# 警告抑制
# ===========================================

# 抑制常见警告
-dontwarn java.lang.invoke.StringConcatFactory
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
