# ===========================================
# Utils Module R8 混淆规则配置
# 工具模块专用混淆规则
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
# 工具类保护
# ===========================================

# 保留所有工具类
-keep class ai.sxwl.android.utils.** { *; }

# 保留所有静态方法
-keepclassmembers class * {
    public static <methods>;
}

# 保留所有单例对象
-keepclassmembers class * {
    public static ** INSTANCE;
    public static ** getInstance();
}

# ===========================================
# Android 系统相关保护
# ===========================================

# 保留Application相关
-keep class * extends android.app.Application { *; }

# 保留Activity相关
-keep class * extends android.app.Activity { *; }

# 保留Service相关
-keep class * extends android.app.Service { *; }

# 保留BroadcastReceiver相关
-keep class * extends android.content.BroadcastReceiver { *; }

# ===========================================
# 文件操作保护
# ===========================================

# 保留文件操作相关类
-keep class java.io.** { *; }
-keep class java.nio.** { *; }

# 保留文件工具类
-keep class ai.sxwl.android.utils.FileUtils { *; }
-keep class ai.sxwl.android.utils.PathUtils { *; }

# ===========================================
# 加密相关保护
# ===========================================

# 保留加密工具类
-keep class ai.sxwl.android.utils.EncryptUtils { *; }
-keep class ai.sxwl.android.utils.EncodeUtils { *; }

# 保留加密相关类
-keep class java.security.** { *; }
-keep class javax.crypto.** { *; }

# ===========================================
# 图片处理保护
# ===========================================

# 保留图片处理工具类
-keep class ai.sxwl.android.utils.ImageCompressUtils { *; }
-keep class ai.sxwl.android.utils.ImageCompressManager { *; }

# ===========================================
# 设备信息保护
# ===========================================

# 保留设备工具类
-keep class ai.sxwl.android.utils.DeviceUtils { *; }

# ===========================================
# 通知相关保护
# ===========================================

# 保留通知工具类
-keep class ai.sxwl.android.utils.NotificationUtils { *; }

# ===========================================
# 语言相关保护
# ===========================================

# 保留语言工具类
-keep class ai.sxwl.android.utils.LanguageUtils { *; }

# ===========================================
# 时间相关保护
# ===========================================

# 保留时间工具类
-keep class ai.sxwl.android.utils.TimeUtils { *; }

# ===========================================
# 日志相关保护
# ===========================================

# 保留日志工具类
-keep class ai.sxwl.android.utils.LogUtils { *; }

# ===========================================
# Toast相关保护
# ===========================================

# 保留Toast工具类
-keep class ai.sxwl.android.utils.ToastUtils { *; }

# ===========================================
# 警告抑制
# ===========================================

# 抑制常见警告
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