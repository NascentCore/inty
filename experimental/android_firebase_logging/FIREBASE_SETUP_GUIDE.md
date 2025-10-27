# Firebase 配置指南

本指南将详细说明如何配置 Firebase 项目以支持 Android 日志采集示例应用。

## 1. 创建 Firebase 项目

### 步骤 1：访问 Firebase Console
1. 打开浏览器，访问 [Firebase Console](https://console.firebase.google.com/)
2. 使用您的 Google 账号登录

### 步骤 2：创建新项目
1. 点击"创建项目"或"Add project"
2. 输入项目名称，例如：`android-logging-sample`
3. 选择是否启用 Google Analytics（推荐启用）
4. 选择 Analytics 账户（如果没有，可以创建新的）
5. 点击"创建项目"

## 2. 添加 Android 应用

### 步骤 1：注册 Android 应用
1. 在 Firebase 项目概览页面，点击"添加应用"图标
2. 选择 Android 平台
3. 输入应用包名：`com.example.firebaselogging`
4. 输入应用昵称：`Firebase Logging Sample`
5. 输入 SHA-1 证书指纹（可选，用于调试）

### 步骤 2：下载配置文件
1. 点击"下载 google-services.json"
2. 将下载的文件重命名为 `google-services.json`
3. 将文件放置在项目的 `app/` 目录下

## 3. 启用 Firebase 服务

### 3.1 启用 Firebase Analytics
1. 在 Firebase Console 左侧菜单中，点击"Analytics"
2. 如果尚未启用，点击"开始使用"
3. 选择数据共享设置（推荐选择默认设置）
4. 点击"完成"

### 3.2 启用 Firebase Crashlytics
1. 在 Firebase Console 左侧菜单中，点击"Crashlytics"
2. 点击"开始使用"
3. 选择要包含的应用（选择您刚创建的 Android 应用）
4. 点击"下一步"
5. 按照说明完成 Crashlytics 设置

### 3.3 启用 Firebase Performance Monitoring
1. 在 Firebase Console 左侧菜单中，点击"Performance"
2. 点击"开始使用"
3. 选择要包含的应用
4. 点击"下一步"
5. 按照说明完成 Performance Monitoring 设置

## 4. 配置应用

### 4.1 验证 google-services.json 文件
确保 `app/google-services.json` 文件包含以下关键信息：
- `project_id`: 您的 Firebase 项目 ID
- `client_id`: OAuth 客户端 ID
- `api_key`: Web API 密钥
- `app_id`: 应用 ID
- `package_name`: 应用包名（应该是 `com.example.firebaselogging`）

### 4.2 检查 Gradle 配置
确保以下文件配置正确：

**项目级 build.gradle.kts:**
```kotlin
plugins {
    id("com.google.gms.google-services") version "4.4.0" apply false
    id("com.google.firebase.crashlytics") version "2.9.9" apply false
}
```

**应用级 build.gradle.kts:**
```kotlin
plugins {
    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
}

dependencies {
    implementation(platform("com.google.firebase:firebase-bom:32.7.0"))
    implementation("com.google.firebase:firebase-analytics-ktx")
    implementation("com.google.firebase:firebase-crashlytics-ktx")
    implementation("com.google.firebase:firebase-perf-ktx")
}
```

## 5. 测试配置

### 5.1 构建和运行应用
1. 使用 Android Studio 打开项目
2. 同步 Gradle 文件
3. 构建并运行应用

### 5.2 验证 Firebase 连接
1. 运行应用后，查看应用内的日志输出
2. 在 Firebase Console 中查看实时事件：
   - Analytics → 事件 → 实时
   - Crashlytics → 问题
   - Performance → 跟踪

### 5.3 测试功能
1. 点击"记录事件"按钮
2. 点击"测试崩溃"按钮（注意：这会崩溃应用）
3. 点击"记录自定义事件"按钮
4. 设置用户属性和用户ID
5. 测试性能监控功能

## 6. 常见问题解决

### 问题 1：应用无法连接到 Firebase
**症状：** 应用启动后没有 Firebase 相关日志
**解决方案：**
- 检查 `google-services.json` 文件是否正确放置在 `app/` 目录
- 确认包名是否匹配
- 检查网络连接
- 查看 Android Studio 的 Logcat 输出

### 问题 2：Analytics 数据不显示
**症状：** 在 Firebase Console 中看不到 Analytics 数据
**解决方案：**
- 等待 24-48 小时（数据有延迟）
- 检查 Firebase Console 中的实时事件
- 确认 Analytics 已启用
- 检查应用是否在后台运行

### 问题 3：Crashlytics 不工作
**症状：** 触发崩溃后，Firebase Console 中没有崩溃报告
**解决方案：**
- 确保已添加 Crashlytics 依赖
- 检查 `google-services.json` 中的 Crashlytics 配置
- 运行测试崩溃验证
- 等待几分钟让数据同步

### 问题 4：构建错误
**症状：** Gradle 构建失败
**解决方案：**
- 检查 Google Services 插件版本
- 确认 Firebase BOM 版本
- 清理项目并重新构建
- 检查 Android SDK 版本

## 7. 安全注意事项

### 7.1 API 密钥安全
- `google-services.json` 文件包含敏感的 API 密钥
- 不要将此文件提交到公共代码仓库
- 在生产环境中使用不同的 Firebase 项目

### 7.2 数据隐私
- 确保遵守当地的数据保护法规
- 在收集用户数据前获得用户同意
- 定期审查收集的数据类型

### 7.3 配额和计费
- 监控 Firebase 使用量
- 设置预算警报
- 了解各服务的定价模式

## 8. 下一步

配置完成后，您可以：
1. 自定义事件参数和用户属性
2. 设置自定义崩溃报告
3. 配置性能监控阈值
4. 集成 Firebase Remote Config
5. 添加 Firebase A/B Testing

## 9. 相关资源

- [Firebase Android 设置指南](https://firebase.google.com/docs/android/setup)
- [Firebase Analytics 文档](https://firebase.google.com/docs/analytics)
- [Firebase Crashlytics 文档](https://firebase.google.com/docs/crashlytics)
- [Firebase Performance Monitoring 文档](https://firebase.google.com/docs/perf-mon)
- [Firebase 控制台](https://console.firebase.google.com/)