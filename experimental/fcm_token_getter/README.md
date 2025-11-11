# FCM Token 获取与注册 Android 应用

本应用用于获取 Firebase Cloud Messaging (FCM) token 并自动注册到后端服务器。

## 功能特性

- 自动获取 FCM token
- 显示 token 内容（可复制）
- 支持手动注册 token 到后端服务器
- 监听 token 刷新事件
- 支持配置后端 API 地址和认证 token

## 项目结构

```
experimental/fcm_token_getter/
├── android_app/
│   ├── app/
│   │   ├── build.gradle.kts
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── java/com/example/fcmtokengetter/
│   │       │   ├── MainActivity.kt
│   │       │   ├── TokenService.kt
│   │       │   ├── ServerConfig.kt
│   │       │   └── FCMTokenService.kt
│   │       └── res/
│   │           ├── layout/activity_main.xml
│   │           └── values/strings.xml
│   ├── build.gradle.kts
│   └── settings.gradle.kts
└── README.md
```

## 集成步骤

### 1. Firebase 配置

**重要提示**：需要的是 Android 客户端配置文件，不是服务端服务账号文件。

1. 前往 [Firebase 控制台](https://console.firebase.google.com/) 创建项目（或使用现有项目）
2. 在项目中添加 Android 应用：
   - 点击项目概览页面的"添加应用"图标（或齿轮图标 → 项目设置）
   - 选择 Android 平台
   - 输入应用包名：`com.example.fcmtokengetter`
   - 输入应用昵称（可选）
   - 点击"注册应用"
3. 下载 `google-services.json` 文件：
   - 在注册应用后，Firebase 会提供下载链接
   - 点击"下载 google-services.json"
   - **注意**：这是客户端配置文件，包含 `project_info` 对象，格式类似 `google-services.json.example`
4. 将下载的 `google-services.json` 文件放入 `android_app/app/` 目录下
   - 文件必须命名为 `google-services.json`（不是其他名称）
   - 文件必须包含 `project_info` 对象和 `client` 数组

### 2. 使用 Android Studio 打开项目

1. 使用 Android Studio 打开 `android_app/` 目录
2. 等待 Gradle 同步完成
3. 连接 Android 设备或启动模拟器

### 3. 配置后端地址

应用默认使用 `http://10.0.2.2:8000` 作为后端地址（适用于 Android 模拟器访问宿主机）。

- **模拟器**：保持默认值 `http://10.0.2.2:8000`
- **真机调试**：改为电脑的局域网 IP 地址，例如 `http://192.168.1.100:8000`
- **生产环境**：改为实际的后端域名，例如 `https://api.example.com`

## 使用方法

### 1. 获取 FCM Token

1. 启动应用
2. 应用会自动获取 FCM token
3. 如果自动获取失败，点击"获取 Token"按钮手动获取
4. Token 会显示在界面上，可以点击"复制 Token"按钮复制到剪贴板

### 2. 注册 Token 到服务器

1. 在"后端 API 地址"输入框中输入后端地址（默认已填充）
2. 在"认证 Token"输入框中输入用户的 Bearer token
3. 点击"注册 Token 到服务器"按钮
4. 等待注册结果，成功或失败都会在界面上显示

### 3. 后端 API 接口

应用会调用以下接口注册 token：

```
POST /api/v1/users/device/register
Authorization: Bearer {auth_token}
Content-Type: application/json

{
  "token": "{fcm_token}"
}
```

## 技术实现

### Token 获取

使用 Firebase SDK 的 `FirebaseMessaging.getInstance().token` 获取 token：

```kotlin
val token = FirebaseMessaging.getInstance().token.await()
```

### Token 刷新监听

实现了 `FCMTokenService` 继承 `FirebaseMessagingService`，监听 token 刷新事件：

```kotlin
override fun onNewToken(token: String) {
    // Token 刷新时的处理逻辑
}
```

### 网络请求

使用 OkHttp 发送 HTTP 请求到后端 API，包含认证头：

```kotlin
val request = Request.Builder()
    .url(url)
    .post(body)
    .addHeader("Authorization", "Bearer $authToken")
    .build()
```

## 注意事项

1. **Firebase 配置**：必须正确配置 `google-services.json` 文件，否则无法获取 token
2. **网络权限**：应用需要网络权限（已在 AndroidManifest.xml 中声明）
3. **认证 Token**：注册 token 时需要有效的用户认证 token
4. **后端地址**：确保设备可以访问后端 API 地址
5. **Token 刷新**：当 token 刷新时，需要重新注册到服务器（当前版本仅记录日志，可扩展自动注册功能）

## 故障排查

### 无法获取 Token

- 检查 `google-services.json` 是否正确配置
  - 确保文件位于 `android_app/app/` 目录下
  - 确保文件包含 `project_info` 对象（不是服务端服务账号文件）
  - 确保 `package_name` 与应用的包名 `com.example.fcmtokengetter` 一致
- 检查 Firebase 项目是否启用了 Cloud Messaging
- 查看 Logcat 日志获取详细错误信息

### 构建错误：Missing project_info object

这个错误通常表示 `google-services.json` 文件格式不正确：

- **错误原因**：使用了服务端服务账号 JSON 文件（包含 `type: "service_account"`），而不是客户端配置文件
- **解决方法**：
  1. 删除错误的文件
  2. 从 Firebase Console 下载正确的 Android 客户端配置文件
  3. 确保文件包含 `project_info` 对象（参考 `google-services.json.example`）
  4. 将文件重命名为 `google-services.json` 并放置在 `android_app/app/` 目录下

### 注册失败

- 检查后端 API 地址是否正确
- 检查认证 token 是否有效
- 检查网络连接是否正常
- 查看 Logcat 日志获取详细错误信息

### 模拟器无法访问后端

- 确保后端服务正在运行
- 模拟器使用 `http://10.0.2.2:8000` 访问宿主机
- 真机需要使用实际的 IP 地址

## 扩展功能

可以扩展以下功能：

1. **自动注册**：在 `FCMTokenService.onNewToken()` 中自动重新注册 token
2. **保存配置**：使用 SharedPreferences 保存后端地址和认证 token
3. **历史记录**：保存已注册的 token 历史
4. **推送测试**：添加测试推送消息的功能

## 参考文档

- [Firebase Cloud Messaging 文档](https://firebase.google.com/docs/cloud-messaging)
- [Firebase Android 设置指南](https://firebase.google.com/docs/android/setup)
- [后端 API 文档](../docs/FCM_DEBUG_GUIDE.md)
