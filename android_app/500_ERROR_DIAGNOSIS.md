# 500错误诊断和解决方案

## 🔍 **问题根本原因 - 已解决！**

**根本原因**: 客户端使用了错误的文件上传方式

### 服务器端错误详情
```
RequestValidationError: [{'type': 'value_error', 'loc': ('body', 'file'), 'msg': "Value error, Expected UploadFile, received: <class 'str'>", 'input': ' ... '}]
```

### 问题分析
- **服务器期望**: `UploadFile` 对象
- **客户端发送**: `FileInputStream` (被序列化为字符串)
- **结果**: FastAPI 验证失败，返回 500 错误

### 调用链分析
```
MySettingViewModel.onSave() 
→ ImageService.uploadImage() 
→ V1UploadImageParams.builder().file(FileInputStream(file))  // ❌ 错误方式
→ IntyNetworkManager.executeRequest() 
→ V1ServiceImpl.uploadImage() 
→ InternalServerException (500)
```

## ✅ **解决方案**

### 修复前 (错误方式)
```kotlin
val params = V1UploadImageParams.builder()
    .file(FileInputStream(file))  // ❌ 错误：使用 FileInputStream
    .croppingAvatar(croppingAvatar)
    .build()
```

### 修复后 (正确方式)
```kotlin
val filePath = Paths.get(filePath)  // ✅ 正确：使用 Path 对象
val params = V1UploadImageParams.builder()
    .file(filePath)  // ✅ 正确：使用 Path 对象
    .croppingAvatar(croppingAvatar)
    .build()
```

### 为什么这样修复？
根据 Inty SDK 文档，推荐的文件上传方式：
1. **Path 对象** (推荐) - 自动处理文件名和内容类型
2. **InputStream** - 需要手动设置文件名
3. **ByteArray** - 适用于内存中的数据

使用 `Path` 对象的好处：
- SDK 自动提取文件名
- 自动设置正确的 MIME 类型
- 服务器端能正确识别为 `UploadFile`

## 💡 **解决方案**

### 立即措施

1. **检查服务器日志**
   ```bash
   # 查看服务器端错误日志
   tail -f /var/log/your-app/error.log
   ```

2. **验证API端点**
   ```bash
   # 使用curl测试API
   curl -X POST "https://dev.inty.sxwl.ai/api/v1/images" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -F "file=@test.jpg" \
        -F "croppingAvatar=true"
   ```

3. **检查服务器资源**
   ```bash
   # 检查磁盘空间
   df -h
   
   # 检查内存使用
   free -h
   
   # 检查进程状态
   ps aux | grep your-app
   ```

### 客户端改进

1. **添加重试机制**
   ```kotlin
   // 在ImageService中添加重试逻辑
   suspend fun uploadImageWithRetry(filePath: String, maxRetries: Int = 3): ApiResult<String> {
       repeat(maxRetries) { attempt ->
           val result = uploadImage(filePath)
           if (result is ApiResult.Success) return result
           
           if (attempt < maxRetries - 1) {
               delay(1000 * (attempt + 1)) // 递增延迟
           }
       }
       return uploadImage(filePath) // 最后一次尝试
   }
   ```

2. **添加文件验证**
   ```kotlin
   // 上传前验证文件
   private fun validateImageFile(file: File): Boolean {
       return file.exists() && 
              file.length() > 0 && 
              file.length() < 10 * 1024 * 1024 && // 10MB限制
              file.extension.lowercase() in listOf("jpg", "jpeg", "png")
   }
   ```

3. **改进错误处理**
   ```kotlin
   // 根据错误类型提供不同处理
   when (result.code) {
       500 -> {
           // 服务器错误，建议重试
           showRetryDialog()
       }
       400 -> {
           // 客户端错误，检查文件
           showFileErrorDialog()
       }
   }
   ```

## 🔧 **调试建议**

### 1. 服务器端调试
- 检查 `/api/v1/images` 端点的实现
- 查看图片处理库的日志
- 验证存储服务的状态
- 检查数据库连接

### 2. 客户端调试
- 尝试上传不同大小的文件
- 测试不同的图片格式
- 检查网络连接稳定性
- 验证认证token有效性

### 3. 环境检查
- 确认开发环境配置正确
- 检查API网关设置
- 验证负载均衡器状态
- 确认CDN配置

## 📋 **下一步行动**

1. **立即**: 检查服务器端日志，找出500错误的具体原因
2. **短期**: 修复服务器端问题或添加重试机制
3. **长期**: 改进错误处理和用户体验

## 🚨 **紧急处理**

如果问题持续存在：
1. 临时禁用图片上传功能
2. 使用备用上传服务
3. 通知用户服务暂时不可用
4. 联系后端团队紧急修复
