# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.kts.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# If your project uses WebView with JS, uncomment the following
# and specify the fully qualified class name to the JavaScript interface
# class:
#-keepclassmembers class fqcn.of.javascript.interface.for.webview {
#   public *;
#}

# Uncomment this to preserve the line number information for
# debugging stack traces.
#-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile

# Moshi 混淆规则 - 确保Kotlin类型能够正确序列化
-keep class com.squareup.moshi.** { *; }
-keep class * extends com.squareup.moshi.JsonAdapter {
    public static com.squareup.moshi.JsonAdapter create();
}

# 保留Kotlin反射相关类
-keep class kotlin.reflect.** { *; }
-keep class kotlin.Metadata { *; }

# 保留数据类
-keepclassmembers class * {
    @com.squareup.moshi.* <methods>;
}

# 保留Moshi注解
-keep @com.squareup.moshi.JsonQualifier interface * { *; }


