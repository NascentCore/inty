# ===========================================
# Core Design Module R8 混淆规则配置
# 核心设计模块专用混淆规则
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
# 设计模块保护
# ===========================================

# 保留所有设计模块类
-keep class ai.sxwl.android.design.** { *; }

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
# 主题相关保护
# ===========================================

# 保留主题相关类
-keep class ai.sxwl.android.design.theme.** { *; }

# 保留颜色相关类
-keep class ai.sxwl.android.design.theme.Color { *; }

# 保留类型相关类
-keep class ai.sxwl.android.design.theme.Type { *; }

# 保留形状相关类
-keep class ai.sxwl.android.design.theme.Shapes { *; }

# ===========================================
# UI组件保护
# ===========================================

# 保留UI组件类
-keep class ai.sxwl.android.design.ui.** { *; }

# 保留通用UI组件
-keep class ai.sxwl.android.design.ui.Common { *; }
-keep class ai.sxwl.android.design.ui.TextField { *; }
-keep class ai.sxwl.android.design.ui.Toolbar { *; }
-keep class ai.sxwl.android.design.ui.Snackbar { *; }
-keep class ai.sxwl.android.design.ui.ListItem { *; }
-keep class ai.sxwl.android.design.ui.Button { *; }
-keep class ai.sxwl.android.design.ui.Shimmer { *; }

# ===========================================
# 工具类保护
# ===========================================

# 保留设计工具类
-keep class ai.sxwl.android.design.UiTools { *; }
-keep class ai.sxwl.android.design.utils.** { *; }

# ===========================================
# 资源相关保护
# ===========================================

# 保留资源相关类
-keep class ai.sxwl.android.design.R { *; }

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
