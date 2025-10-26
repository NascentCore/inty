# 后端500错误详细信息返回机制

## 🎯 **问题背景**

Android 应用很难看到服务器端的详细错误信息，导致调试困难。之前的500错误只返回空消息，无法了解具体的错误原因。

## ✅ **解决方案**

### 1. 后端改进

#### 添加通用错误处理器
在 `app/middleware/error_handler.py` 中添加了 `general_exception_handler`：

```python
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions (500 errors)"""
    # 详细记录错误信息到日志
    logger.error(f"=== 通用服务器错误 (500错误) ===")
    logger.error(f"异常类型: {type(exc).__name__}")
    logger.error(f"异常消息: {str(exc)}")
    logger.error(f"异常堆栈跟踪:")
    logger.error(traceback.format_exc())
    
    # 根据环境返回不同详细程度的错误信息
    if global_config_loaded_from_config_yaml.app.debug:
        # 调试模式：返回详细错误信息
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"Internal server error: {str(exc)}",
                "data": {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                    "request_info": {
                        "method": request.method,
                        "url": str(request.url),
                        "path": request.url.path,
                    }
                },
            },
        )
    else:
        # 生产模式：返回通用错误信息
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal server error",
                "data": None,
            },
        )
```

#### 注册错误处理器
在 `app/main.py` 中注册通用错误处理器：

```python
# 注册通用异常处理器 - 必须放在最后，作为兜底处理器
app.add_exception_handler(Exception, general_exception_handler)
```

### 2. Android端改进

#### 增强错误日志记录
在 `IntyNetworkManager.kt` 中添加了服务器错误体的解析：

```kotlin
is com.inty.api.errors.InternalServerException -> {
    LogUtils.e("IntyNetworkManager: Internal Server Error (500) - ${e.message}")
    LogUtils.e("IntyNetworkManager: Server error details: ${e.toString()}")
    
    // 尝试解析服务器返回的详细错误信息
    try {
        val errorBody = e.body
        if (errorBody != null) {
            LogUtils.e("IntyNetworkManager: Server error body: $errorBody")
        }
    } catch (ex: Exception) {
        LogUtils.e("IntyNetworkManager: Failed to parse error body: ${ex.message}")
    }
}
```

## 🔍 **效果对比**

### 修复前
```
API exception: 500: 
API exception type: InternalServerException
```

### 修复后（调试模式）
```
API exception: 500: Internal server error: Expected UploadFile, received: <class 'str'>
API exception type: InternalServerException
IntyNetworkManager: Server error body: {
  "code": 500,
  "message": "Internal server error: Expected UploadFile, received: <class 'str'>",
  "data": {
    "error_type": "RequestValidationError",
    "error_message": "Expected UploadFile, received: <class 'str'>",
    "traceback": "Traceback (most recent call last):\n...",
    "request_info": {
      "method": "POST",
      "url": "https://dev.inty.sxwl.ai/api/v1/images",
      "path": "/api/v1/images"
    }
  }
}
```

## 🎯 **优势**

1. **详细错误信息**: 在调试模式下，Android应用可以看到完整的错误堆栈跟踪
2. **环境区分**: 生产环境不暴露敏感信息，调试环境提供详细信息
3. **请求上下文**: 包含请求方法、URL等上下文信息
4. **错误类型识别**: 明确显示异常类型和消息
5. **向后兼容**: 不影响现有的错误处理逻辑

## 🚀 **使用方法**

### 调试模式
- 设置 `app.debug = true` 在配置文件中
- Android应用将收到详细的错误信息
- 便于开发和调试

### 生产模式
- 设置 `app.debug = false` 在配置文件中
- Android应用只收到通用错误信息
- 保护服务器安全

## 📋 **注意事项**

1. **安全考虑**: 生产环境不应暴露详细的错误堆栈
2. **性能影响**: 错误处理器会增加少量性能开销
3. **日志大小**: 详细错误信息会增加日志文件大小
4. **敏感信息**: 确保不记录敏感的用户数据或密钥

## 🔧 **未来改进**

1. **错误分类**: 根据错误类型提供不同的处理策略
2. **用户友好**: 将技术错误转换为用户友好的提示
3. **错误统计**: 收集和分析错误统计信息
4. **自动重试**: 对特定类型的错误实现自动重试机制
