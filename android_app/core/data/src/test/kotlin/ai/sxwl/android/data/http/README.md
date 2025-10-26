# HTTP 500错误处理测试

## 🎯 **测试目的**

这些测试展示了Android应用中HTTP 500错误处理的完整行为，包括：

1. **ApiResult异常转换机制**
2. **HTTP状态码映射**
3. **错误信息详细记录**
4. **完整错误处理流程**
5. **用户友好的错误消息**

## 📁 **测试文件结构**

```
android_app/core/data/src/test/kotlin/ai/sxwl/android/data/http/
├── Http500ErrorHandlingTest.kt              # 单元测试
├── Http500ErrorHandlingIntegrationTest.kt   # 集成测试
└── run_http_500_tests.sh                    # 测试运行脚本
```

## 🧪 **测试类型**

### 1. **单元测试** (`Http500ErrorHandlingTest.kt`)

测试 `ApiResult` 和异常转换的核心功能：

```kotlin
@Test
fun `test InternalServerException converts to 500 error`() = runTest {
    // Given: 模拟500服务器内部错误
    val serverException = InternalServerException.builder()
        .statusCode(500)
        .body("{\"code\":500,\"message\":\"Internal server error\"}")
        .build()

    // When: 将异常转换为ApiResult
    val result: ApiResult<String> = serverException.toApiResult()

    // Then: 验证结果
    assertTrue("Result should be Error", result is ApiResult.Error)
    val errorResult = result as ApiResult.Error
    
    assertEquals("HTTP code should be 500", 500, errorResult.code)
    assertEquals("Message should match exception", serverException.message, errorResult.message)
    assertEquals("Exception should be preserved", serverException, errorResult.exception)
}
```

**测试场景**：
- ✅ InternalServerException (500) → ApiResult.Error(code=500)
- ✅ BadRequestException (400) → ApiResult.Error(code=400)
- ✅ UnauthorizedException (401) → ApiResult.Error(code=401)
- ✅ NotFoundException (404) → ApiResult.Error(code=404)
- ✅ Unknown Exception → ApiResult.Error(code=-1)
- ✅ Success Case → ApiResult.Success(data)

### 2. **集成测试** (`Http500ErrorHandlingIntegrationTest.kt`)

测试完整的错误处理流程：

```kotlin
@Test
fun `test complete 500 error flow from ImageService to ApiResult`() = runTest {
    // Given: 模拟服务器返回500错误
    val serverException = InternalServerException.builder()
        .statusCode(500)
        .body("""{
            "code": 500,
            "message": "Internal server error: Expected UploadFile, received: <class 'str'>",
            "data": {
                "error_type": "RequestValidationError",
                "error_message": "Expected UploadFile, received: <class 'str'>",
                "traceback": "Traceback (most recent call last):...",
                "request_info": {
                    "method": "POST",
                    "url": "https://dev.inty.sxwl.ai/api/v1/images",
                    "path": "/api/v1/images"
                }
            }
        }""")
        .build()

    // When: 调用ImageService上传图片
    val result = ImageService.uploadImage(testFilePath, croppingAvatar = true)

    // Then: 验证完整的错误处理流程
    assertTrue("Result should be Error", result is ApiResult.Error)
    val errorResult = result as ApiResult.Error
    
    assertEquals("HTTP code should be 500", 500, errorResult.code)
    assertEquals("Message should match exception", serverException.message, errorResult.message)
    assertEquals("Exception should be preserved", serverException, errorResult.exception)
}
```

**测试场景**：
- ✅ 完整的ImageService → IntyNetworkManager → ApiResult错误流程
- ✅ ViewModel中的用户友好错误消息映射
- ✅ 错误在多层调用中的传播
- ✅ 不同类型异常的处理
- ✅ 成功案例的对比测试

## 🚀 **运行测试**

### 方法1：使用测试脚本
```bash
cd android_app
chmod +x run_http_500_tests.sh
./run_http_500_tests.sh
```

### 方法2：使用Gradle命令
```bash
# 运行单元测试
./gradlew :core:data:testDebugUnitTest --tests="*Http500ErrorHandlingTest*"

# 运行集成测试
./gradlew :core:data:testDebugUnitTest --tests="*Http500ErrorHandlingIntegrationTest*"

# 运行所有HTTP 500相关测试
./gradlew :core:data:testDebugUnitTest --tests="*Http500ErrorHandling*"
```

### 方法3：在Android Studio中运行
1. 打开 `Http500ErrorHandlingTest.kt` 或 `Http500ErrorHandlingIntegrationTest.kt`
2. 右键点击类名或方法名
3. 选择 "Run 'TestName'"

## 📊 **测试验证的行为**

### 1. **类型安全**
```kotlin
// ✅ 编译时检查，不会遗漏错误处理
when (result) {
    is ApiResult.Success -> handleSuccess(result.data)
    is ApiResult.Error -> handleError(result.code, result.message)
    // 编译器确保所有情况都被处理
}
```

### 2. **统一错误处理**
```kotlin
// ✅ 所有API调用都返回相同的错误格式
val userResult: ApiResult<User> = userService.getUser()
val imageResult: ApiResult<String> = imageService.uploadImage()
val chatResult: ApiResult<Chat> = chatService.sendMessage()

// 统一的错误处理逻辑
fun handleApiResult(result: ApiResult<*>) {
    when (result) {
        is ApiResult.Success -> { /* 成功处理 */ }
        is ApiResult.Error -> { /* 错误处理 */ }
    }
}
```

### 3. **详细错误信息**
```kotlin
// ✅ 保留完整的错误上下文
is ApiResult.Error -> {
    LogUtils.e("Error code: ${result.code}")
    LogUtils.e("Error message: ${result.message}")
    LogUtils.e("Original exception: ${result.exception}")
    // 可以访问原始异常进行进一步分析
}
```

### 4. **用户友好错误消息**
```kotlin
// ✅ ViewModel中的错误消息映射
val errorMessage = when (result.code) {
    500 -> "服务器内部错误，请稍后重试"
    400 -> "图片格式不支持或文件过大"
    401 -> "登录已过期，请重新登录"
    403 -> "没有权限上传图片"
    404 -> "上传服务不可用"
    else -> result.message ?: "上传失败，请重试"
}
```

## 🔍 **测试覆盖的关键场景**

### 异常类型映射
| 异常类型 | HTTP状态码 | 测试验证 |
|---------|-----------|---------|
| InternalServerException | 500 | ✅ |
| BadRequestException | 400 | ✅ |
| UnauthorizedException | 401 | ✅ |
| NotFoundException | 404 | ✅ |
| Unknown Exception | -1 | ✅ |

### 错误处理流程
| 步骤 | 测试验证 |
|-----|---------|
| API调用失败 | ✅ |
| 异常捕获 | ✅ |
| 转换为ApiResult.Error | ✅ |
| 日志记录 | ✅ |
| 错误传播 | ✅ |
| 用户友好消息 | ✅ |

### 成功案例
| 场景 | 测试验证 |
|-----|---------|
| API调用成功 | ✅ |
| 转换为ApiResult.Success | ✅ |
| 数据提取 | ✅ |
| 成功日志 | ✅ |

## 📝 **测试输出示例**

```
🚀 运行HTTP 500错误处理测试
==================================

📋 测试覆盖范围：
1. ApiResult异常转换行为
2. HTTP状态码映射
3. 错误信息详细记录
4. 完整错误处理流程
5. ViewModel中的用户友好错误消息

🧪 运行单元测试...
✅ test InternalServerException converts to 500 error
✅ test BadRequestException converts to 400 error
✅ test UnauthorizedException converts to 401 error
✅ test NotFoundException converts to 404 error
✅ test unknown exception converts to -1 error code
✅ test executeApiCall with success
✅ test executeApiCall with exception
✅ test ApiResult Success behavior
✅ test ApiResult Error behavior
✅ test pattern matching with when expression
✅ test error handling in ViewModel context
✅ test error logging behavior

🔗 运行集成测试...
✅ test complete 500 error flow from ImageService to ApiResult
✅ test error handling in ViewModel context with user-friendly messages
✅ test error propagation through multiple layers
✅ test error handling with different exception types
✅ test success case for comparison
✅ test error handling with null message

📊 测试结果分析：
✅ ApiResult.Success - 成功处理API响应
✅ ApiResult.Error - 错误状态码和消息正确映射
✅ 异常转换 - Exception.toApiResult()正确工作
✅ 日志记录 - 详细的错误信息被记录
✅ 错误传播 - 错误在调用链中正确传播
✅ 用户友好消息 - ViewModel中的错误消息映射

✨ 测试完成！HTTP 500错误处理机制已验证。
```

## 🎯 **总结**

这些测试全面验证了HTTP 500错误处理机制的正确性，确保：

1. **异常正确转换** - 各种异常类型都能正确映射到HTTP状态码
2. **错误信息保留** - 原始异常和错误消息被完整保留
3. **日志详细记录** - 调试信息被正确记录
4. **用户友好体验** - 技术错误被转换为用户可理解的提示
5. **类型安全** - 编译时确保错误处理的完整性

通过这些测试，开发者可以确信HTTP 500错误处理机制能够正确工作，为Android应用提供可靠的错误处理能力。
