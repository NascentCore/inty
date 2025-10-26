# 调试日志增强 - 500错误排查

## 概述

为了帮助调试图片上传过程中的500错误，我们在关键组件中添加了详细的日志记录。这些日志将帮助识别问题的根本原因。

## 增强的组件

### 1. ImageService.uploadImage()
**文件**: `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/services/ImageService.kt`

**新增日志**:
- 上传开始时的文件路径和参数
- 文件存在性检查和文件大小
- 请求参数创建确认
- 服务器响应接收确认
- 响应数据内容详情
- URL提取成功确认

### 2. IntyNetworkManager.executeRequest()
**文件**: `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/IntyNetworkManager.kt`

**新增日志**:
- 请求开始时的超时配置
- 详细的异常类型和消息
- 完整的异常堆栈跟踪
- HTTP状态码和响应体（针对HttpException）
- 网络超时、连接失败、IO异常的特殊处理

### 3. ApiResult.toApiResult()
**文件**: `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/ApiResult.kt`

**新增日志**:
- 异常类型识别
- 完整的异常堆栈跟踪
- HTTP状态码提取（针对HttpException）

### 4. CreateRoleActivity
**文件**: `android_app/app/src/main/kotlin/com/ai/intellimate/agent/generate/CreateRoleActivity.kt`

**新增日志**:
- 头像上传前的文件信息
- 上传协程启动确认
- 上传结果类型识别
- 详细的错误信息（包括错误码和异常）
- Agent创建/更新请求的详细信息
- 请求参数和响应处理

### 5. MySettingViewModel.onSave()
**文件**: `android_app/app/src/main/kotlin/com/ai/intellimate/profile/MySettingViewModel.kt`

**新增日志**:
- 保存操作开始确认
- 头像变更状态检查
- 头像URI和路径信息
- 上传结果类型识别
- 用户资料更新状态
- 完整的异常处理

## 日志级别说明

- **LogUtils.d()**: 调试信息 - 正常流程跟踪
- **LogUtils.i()**: 信息 - 成功操作确认
- **LogUtils.e()**: 错误 - 失败和异常情况

## 预期的调试信息

当500错误发生时，现在应该能看到：

1. **文件信息**: 文件路径、大小、存在性
2. **网络请求详情**: 超时配置、请求参数
3. **服务器响应**: HTTP状态码、响应体内容
4. **异常详情**: 异常类型、消息、完整堆栈跟踪
5. **处理流程**: 每个步骤的执行状态

## 使用方法

1. 重现500错误
2. 查看logcat输出，搜索以下标签：
   - `ImageService:`
   - `IntyNetworkManager:`
   - `CreateRoleActivity:`
   - `MySettingViewModel:`
3. 分析日志中的错误信息和异常堆栈
4. 根据HTTP状态码和响应体确定服务器端问题

## 注意事项

- 这些日志在生产环境中应该被适当控制
- 敏感信息（如API密钥）不会被记录
- 日志级别可以通过NetworkConfig.shouldEnableDetailedLogging()控制

## 下一步

根据日志输出分析500错误的具体原因，可能需要：
1. 检查服务器端日志
2. 验证API端点配置
3. 检查文件上传限制
4. 验证认证和权限设置
