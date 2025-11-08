package com.ai.plugins

/** 用于统一管理项目参数、业务key等配置的文件 */
object ProjectConfig {

    // 用于构建项目需要的一些通用参数、业务key等配置都可以统一在此管理

    val compileVersion = 36 // navigation,emoji等新版本的依赖库，都要求compile 34才行
    val targetVersion = 36
    val minSdkVersion = 29

    val versionName = "1.2.4"
}
