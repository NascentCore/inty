/*
 * 版权所有2022 Android 开源Project
 *
 * 根据 Apache License 2.0 版（“许可证”）获得许可；
 * 放弃许可证，否则您无法使用此文件。
 *您可以在以下位置获取许可证副本：
 *
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * 除非适用法律要求或书面同意，否则软件
 * 根据许可证发放是在“按原样”基础上发放的，
 * 不提供任何类型的保证或条件，无论是 express 或暗示的。
 * 请参阅许可证以了解特定语言的管理权限和
 * 许可证的下限制。*/

dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        maven(url = "https://maven.aliyun.com/repository/public/")
    }
// 这里暂时引用的tom或者外部工程的目录，build-logic内的，暂时bak使用，后续尝试开发IDE插件创建模版工程project
    versionCatalogs { create("libs") { from(files("../gradle/libs.versions.toml")) } }
}

rootProject.name = "build-logic"

include(":convention")
