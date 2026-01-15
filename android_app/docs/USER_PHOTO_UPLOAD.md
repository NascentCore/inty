# 用户图片（user_photo）上传功能文档

> **CREATED_BY_AGENT**: 本文档由 AI Agent 创建，用于说明用户图片上传功能的技术实现和操作方式。

## 功能概述

用户图片（user_photo）上传功能允许用户上传自己的照片作为个人外观参考。该功能支持从相册选择图片或使用相机拍照，上传的图片会自动进行格式转换和压缩处理，最终保存到用户资料中。

## 技术实现架构

### 架构层次

```
UI层 (UploadSelfieScreen)
    ↓
ViewModel层 (ModifyProfileViewModel)
    ↓
Repository层 (UserProfileRepository)
    ↓
DataSource层 (UserProfileDataSource)
    ↓
API层 (IUserApi)
    ↓
网络层 (Retrofit + OkHttp)
```

### 核心组件

#### 1. UI层
- **文件位置**: `app/src/main/kotlin/com/ai/intellimate/profile/UploadSelfieScreen.kt`
- **功能**: 提供用户界面，支持从相册选择或相机拍照
- **关键特性**:
  - 使用 `ActivityResultContracts.PickVisualMedia()` 选择相册图片
  - 使用 `ActivityResultContracts.TakePicture()` 进行拍照
  - 显示上传进度和已上传的图片预览

#### 2. ViewModel层
- **文件位置**: `app/src/main/kotlin/com/ai/intellimate/profile/ModifyProfileViewModel.kt`
- **核心方法**: `setUserAppearance(uri: Uri, callback: (() -> Unit)?)`
- **功能**:
  - 处理图片 URI 转换
  - 调用图片压缩和格式转换
  - 调用 Repository 更新用户资料
  - 管理上传状态

#### 3. Repository层
- **文件位置**: `app/src/main/kotlin/com/ai/intellimate/profile/data/UserProfileRepository.kt`
- **核心方法**: `updateUserAppearance(userProfile: UserProfile, file: File)`
- **功能**:
  - 协调图片上传和用户资料更新
  - 先上传图片获取 URL，再更新用户资料
  - 保存更新后的用户资料到本地

#### 4. DataSource层
- **文件位置**: `app/src/main/kotlin/com/ai/intellimate/profile/data/UserProfileDataSource.kt`
- **核心方法**: `uploadImage(file: File)`
- **功能**:
  - 将图片文件转换为 MultipartBody
  - 调用 API 上传图片
  - 返回上传后的图片 URL

#### 5. API层
- **接口定义**: `core/data/src/main/kotlin/ai/sxwl/android/data/api/IUserApi.kt`
- **接口方法**:
  ```kotlin
  @Multipart
  @POST("/api/v1/images")
  suspend fun uploadAvatar(@Part file: MultipartBody.Part): HttpResult<UploadAvatarResponse>
  ```

## API接口说明

### 上传图片接口

**端点**: `POST /api/v1/images`

**请求格式**: `multipart/form-data`

**请求参数**:
- `file`: MultipartBody.Part，图片文件

**响应格式**:
```kotlin
data class UploadAvatarResponse(
    @Json(name = "url") val url: String = "",
    @Json(name = "avatar_url") val avatar_url: String = "",
)
```

**响应字段说明**:
- `url`: 上传后的图片 URL（用于 user_photo 字段）
- `avatar_url`: 头像 URL（用于 avatar 字段）

### 更新用户资料接口

**端点**: `PUT /api/v1/users/profile` (通过 IntyUserProfileSDK)

**请求体**:
```kotlin
data class UserProfile(
    @param:Json(name = "user_photo") val userPhoto: String? = null,
    // ... 其他字段
)
```

## 数据流程

### 完整上传流程

1. **用户选择图片**
   - 用户点击"从相册选择"或"拍照"按钮
   - 系统打开相册选择器或相机应用
   - 用户选择/拍摄图片后返回 URI

2. **图片处理**
   - 将 URI 转换为临时文件 (`createTempFileFromUri`)
   - 转换为 JPG 格式并压缩到 2MB 以内 (`convertToJpgAndCompress`)
   - 清理临时文件

3. **图片上传**
   - 将文件转换为 `MultipartBody.Part`
   - 调用 `IUserApi.uploadAvatar()` 上传
   - 获取返回的图片 URL

4. **更新用户资料**
   - 使用获取的 URL 更新 `UserProfile.userPhoto` 字段
   - 调用 `IntyUserProfileSDK.updateUserProfile()` 更新服务器
   - 保存更新后的资料到本地 (`UserProfileManager`)

5. **UI反馈**
   - 显示上传成功提示
   - 更新界面显示新上传的图片

## 图片处理逻辑

### 压缩策略

图片处理在 `ModifyProfileViewModel.convertToJpgAndCompress()` 方法中实现：

1. **格式转换**: 所有图片统一转换为 JPG 格式
2. **尺寸限制**: 最大尺寸不超过 1920x1920 像素
3. **文件大小限制**: 压缩到 2MB (2048KB) 以内
4. **压缩算法**:
   - 使用二分法查找合适的 JPEG 质量值（30-100）
   - 如果质量降到最低仍超过大小限制，则进一步缩小图片尺寸
   - 最小尺寸限制为 800x800 像素

### 压缩流程

```
原始图片
    ↓
检查文件大小
    ↓
如果 ≤ 2MB: 直接转换格式
如果 > 2MB: 进行压缩处理
    ↓
计算缩放比例（最大 1920x1920）
    ↓
加载缩放后的 Bitmap
    ↓
使用二分法查找合适的质量值
    ↓
如果仍超过大小: 进一步缩小尺寸（最小 800x800）
    ↓
输出压缩后的 JPG 文件
```

### 内存管理

- 使用 `Bitmap.recycle()` 及时释放内存
- 临时文件在处理完成后立即删除
- 使用 `Dispatchers.IO` 在后台线程处理图片

## 功能操作方式

### 用户操作步骤

1. **进入上传页面**
   - 路径: 个人中心（Me） → 编辑个人资料（Edit My Persona） → 上传自拍（Upload Selfie）

2. **选择图片来源**
   - **从相册选择**: 点击"Choose a photo"按钮，从相册中选择图片
   - **拍照**: 点击"Take a selfie"按钮，使用相机拍摄照片

3. **自动处理**
   - 系统自动进行图片格式转换和压缩
   - 显示上传进度指示器

4. **完成上传**
   - 上传成功后显示提示信息
   - 图片自动保存到用户资料中
   - 返回编辑页面，可以看到已上传的图片

### UI界面说明

**UploadSelfieScreen** 界面包含：

1. **顶部导航栏**: 显示"Upload Selfie"标题和返回按钮
2. **图片预览区域**: 显示当前已上传的用户图片（如果有）
3. **功能说明文字**:
   - 标题: "Be the protagonist in your own dialogue"
   - 描述: "To make the generated image look more like you, you can upload a selfie as a reference."
4. **操作按钮**:
   - "Choose a photo": 从相册选择图片
   - "Take a selfie": 使用相机拍照
5. **加载状态**: 上传过程中显示圆形进度指示器

### 字符串资源

相关字符串定义在 `app/src/main/res/values/strings.xml`:

- `str_appearance`: "Upload Selfie"
- `image_picker_gallery`: "Choose a photo"
- `image_picker_camera`: "Take a selfie"
- `image_pick_protagonist_title`: "Be the protagonist in your own dialogue"
- `image_pick_reference_description`: "To make the generated image look more like you, you can upload a selfie as a reference."
- `saved_successfully`: "Saved successfully"

## 相关文件位置

### 核心实现文件

- **UI组件**: `app/src/main/kotlin/com/ai/intellimate/profile/UploadSelfieScreen.kt`
- **ViewModel**: `app/src/main/kotlin/com/ai/intellimate/profile/ModifyProfileViewModel.kt`
- **Repository**: `app/src/main/kotlin/com/ai/intellimate/profile/data/UserProfileRepository.kt`
- **DataSource**: `app/src/main/kotlin/com/ai/intellimate/profile/data/UserProfileDataSource.kt`
- **API接口**: `core/data/src/main/kotlin/ai/sxwl/android/data/api/IUserApi.kt`

### 数据模型文件

- **用户资料模型**: `core/data/src/main/kotlin/ai/sxwl/android/data/api/model/UserBean.kt`
- **上传响应模型**: `core/data/src/main/kotlin/ai/sxwl/android/data/api/model/AgentBean.kt` (UploadAvatarResponse)

### 配置文件

- **字符串资源**: `app/src/main/res/values/strings.xml`
- **文件提供者配置**: `app/src/main/res/xml/file_paths.xml` (用于相机拍照的文件 URI)

## 注意事项

1. **权限要求**:
   - 相册访问需要 `READ_MEDIA_IMAGES` 权限（Android 13+）
   - 相机使用需要 `CAMERA` 权限

2. **文件大小限制**:
   - 上传前会自动压缩到 2MB 以内
   - 如果原始图片过大，压缩后可能影响图片质量

3. **格式支持**:
   - 支持常见图片格式（JPG、PNG、WEBP 等）
   - 最终统一转换为 JPG 格式

4. **网络错误处理**:
   - 使用 `NetworkErrorHandler` 统一处理网络错误
   - 上传失败时会显示错误提示

5. **临时文件清理**:
   - 所有临时文件在处理完成后自动删除
   - 避免占用设备存储空间

## 技术细节

### 图片压缩参数

- **最大尺寸**: 1920x1920 像素
- **最小尺寸**: 800x800 像素
- **最大文件大小**: 2048 KB (2 MB)
- **JPEG 质量范围**: 30-100
- **压缩策略**: 二分法查找 + 尺寸缩放

### 网络请求配置

- **Content-Type**: `multipart/form-data`
- **文件字段名**: `file`
- **请求超时**: 由 Retrofit/OkHttp 配置决定
- **重试机制**: 由网络层统一处理

### 状态管理

- 使用 `StateFlow` 管理上传状态 (`isAppearanceUploading`)
- 使用 `StateFlow` 管理用户资料 (`userProfile`)
- 使用 `SharedFlow` 管理一次性事件通知

## 后续优化建议

1. **图片裁剪功能**: 可以添加图片裁剪功能，让用户在上传前调整图片
2. **多图上传**: 支持上传多张图片作为参考
3. **上传进度显示**: 显示具体的上传进度百分比
4. **图片预览优化**: 支持放大查看已上传的图片
5. **错误重试机制**: 上传失败时提供重试按钮
