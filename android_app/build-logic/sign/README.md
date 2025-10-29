# sign - 签名配置

## 概述

本项目使用JSON格式的配置文件来管理Android应用的签名密钥信息，通过`SignKeyConfig`类读取配置并提供给Gradle插件使用。

## 修复说明

已修复kotlinx-serialization版本兼容性问题，现在使用Gson进行JSON解析，确保与Kotlin 2.2.0兼容。

## 配置文件

### signing-config.json

签名配置文件位于 `build-logic/sign/signing-config.json`，包含以下结构(示例)：

```json
{
  "debug": {
    "storeFile": "sign/key.jks",
    "storePassword": "inty.sxwl.ai",
    "keyAlias": "key0",
    "keyPassword": "inty.sxwl.ai"
  },
  "release": {
    "storeFile": "sign/release.jks",
    "storePassword": "heartmate.inty.cc",
    "keyAlias": "my-key-alias",
    "keyPassword": "heartmate.inty.cc"
  }
}
```

## 使用方法

### 在Gradle脚本中使用

```kotlin
// 在build.gradle.kts中
import com.ai.plugins.SignKeyConfig

android {
    signingConfigs {
        create("debug") {
            storeFile = file(SignKeyConfig.DEBUG_STORE_FILE)
            storePassword = SignKeyConfig.DEBUG_STORE_PASSWORD
            keyAlias = SignKeyConfig.DEBUG_KEY_ALIAS
            keyPassword = SignKeyConfig.DEBUG_KEY_PASSWORD
        }

        create("release") {
            storeFile = file(SignKeyConfig.RELEASE_STORE_FILE)
            storePassword = SignKeyConfig.RELEASE_STORE_PASSWORD
            keyAlias = SignKeyConfig.RELEASE_KEY_ALIAS
            keyPassword = SignKeyConfig.RELEASE_KEY_PASSWORD
        }
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("debug")
        }
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

## 可用的常量

### Debug 签名配置

- `SignKeyConfig.DEBUG_STORE_FILE` - 密钥库文件路径
- `SignKeyConfig.DEBUG_STORE_PASSWORD` - 密钥库密码
- `SignKeyConfig.DEBUG_KEY_ALIAS` - 密钥别名
- `SignKeyConfig.DEBUG_KEY_PASSWORD` - 密钥密码

### Release 签名配置

- `SignKeyConfig.RELEASE_STORE_FILE` - 密钥库文件路径
- `SignKeyConfig.RELEASE_STORE_PASSWORD` - 密钥库密码
- `SignKeyConfig.RELEASE_KEY_ALIAS` - 密钥别名
- `SignKeyConfig.RELEASE_KEY_PASSWORD` - 密钥密码

## 技术实现

- 使用Gson进行JSON解析，确保与Kotlin 2.2.0兼容
- 懒加载机制，只在需要时读取配置
- 错误处理，配置文件不存在时抛出异常
- 类型安全的数据类定义

## 安全注意事项

1. **不要将签名配置文件提交到版本控制**：确保 `signing-config.json` 文件已添加到 `.gitignore`
1. **密钥文件安全**：确保 `.jks` 文件也添加到 `.gitignore`
1. **密码保护**：考虑使用环境变量或加密存储敏感信息

## 故障排除

如果遇到问题，请检查：

1. 配置文件路径是否正确
1. JSON格式是否有效
1. 所有必需的字段是否都已填写
1. 密钥文件是否存在

## 依赖要求

系统使用以下依赖：

- `gson:2.13.1` - JSON解析
- `kotlin-stdlib` - Kotlin标准库

## Cursor Summary

- 目录用途: 约定式构建中的签名配置支持（读取 `signing-config.json`），为模块提供 `debug/release` 签名参数。
- 关键能力: `SignKeyConfig` 使用 Gson 解析 JSON，暴露常量以供 Gradle 脚本引用；支持懒加载与错误处理。
- 安全建议: 不将签名文件与配置提交到版本库，敏感信息通过环境变量或安全存储管理。
