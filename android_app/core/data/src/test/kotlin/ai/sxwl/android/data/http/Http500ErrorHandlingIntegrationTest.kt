package ai.sxwl.android.data.http

import ai.sxwl.android.data.http.services.ImageService
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import com.inty.api.errors.InternalServerException
import com.inty.api.client.IntyClient
import com.inty.api.models.api.v1.V1UploadImageParams
import com.inty.api.models.api.v1.report.ApiResponseDict
import io.mockk.*
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import java.io.File
import java.nio.file.Paths

/**
 * 集成测试：展示完整的HTTP 500错误处理流程
 * 
 * 这个测试展示了：
 * 1. ImageService如何处理文件上传错误
 * 2. IntyNetworkManager如何执行请求和捕获异常
 * 3. ApiResult如何在整个调用链中传播错误
 * 4. 完整的错误处理流程从API调用到错误响应
 */
class Http500ErrorHandlingIntegrationTest {

    private lateinit var mockIntyClient: IntyClient
    private lateinit var mockApiResponse: ApiResponseDict

    @Before
    fun setup() {
        // 模拟LogUtils
        mockkStatic(LogUtils::class)
        every { LogUtils.e(any<String>()) } just Runs
        every { LogUtils.e(any<String>(), any<Throwable>()) } just Runs
        every { LogUtils.d(any<String>()) } just Runs
        every { LogUtils.i(any<String>()) } just Runs
        
        // 模拟NetworkConfig
        mockkObject(NetworkConfig)
        every { NetworkConfig.shouldEnableDetailedLogging() } returns true
        
        // 模拟IntyClient和相关组件
        setupMockIntyClient()
    }

    private fun setupMockIntyClient() {
        mockIntyClient = mockk<IntyClient>()
        mockApiResponse = mockk<ApiResponseDict>()
        
        // 模拟IntyNetworkManager.getClient()
        mockkObject(IntyNetworkManager)
        every { IntyNetworkManager.getClient() } returns mockIntyClient
    }

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

        // 模拟API调用抛出异常
        val mockApi = mockk<com.inty.api.services.blocking.api.V1Service>()
        val mockV1Api = mockk<com.inty.api.services.blocking.api.V1ServiceImpl>()
        
        every { mockIntyClient.api() } returns mockk {
            every { v1() } returns mockV1Api
        }
        
        every { mockV1Api.uploadImage(any<V1UploadImageParams>()) } throws serverException

        // When: 调用ImageService上传图片
        val testFilePath = "/test/path/image.jpg"
        val result = ImageService.uploadImage(testFilePath, croppingAvatar = true)

        // Then: 验证完整的错误处理流程
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        
        // 验证错误信息
        assertEquals("HTTP code should be 500", 500, errorResult.code)
        assertEquals("Message should match exception", serverException.message, errorResult.message)
        assertEquals("Exception should be preserved", serverException, errorResult.exception)
        
        // 验证日志记录
        verify { LogUtils.d("ImageService: Starting image upload - filePath: $testFilePath, croppingAvatar: true") }
        verify { LogUtils.e("IntyNetworkManager: Upload Image failed with exception: InternalServerException") }
        verify { LogUtils.e("IntyNetworkManager: Exception message: ${serverException.message}") }
        verify { LogUtils.e("IntyNetworkManager: Server error body: ${serverException.body}") }
        verify { LogUtils.e("API exception: ${serverException.message}") }
        verify { LogUtils.e("API exception type: InternalServerException") }
        verify { LogUtils.e("API exception HTTP code: 500") }
    }

    @Test
    fun `test error handling in ViewModel context with user-friendly messages`() = runTest {
        // Given: 模拟不同类型的服务器错误
        val testCases = listOf(
            InternalServerException.builder().statusCode(500).body("Server error").build() to "服务器内部错误，请稍后重试",
            InternalServerException.builder().statusCode(400).body("Bad request").build() to "图片格式不支持或文件过大",
            InternalServerException.builder().statusCode(401).body("Unauthorized").build() to "登录已过期，请重新登录",
            InternalServerException.builder().statusCode(403).body("Forbidden").build() to "没有权限上传图片",
            InternalServerException.builder().statusCode(404).body("Not found").build() to "上传服务不可用"
        )

        testCases.forEach { (exception, expectedMessage) ->
            // When: 将异常转换为ApiResult
            val result: ApiResult<String> = exception.toApiResult()

            // Then: 验证ViewModel中的错误处理逻辑
            when (result) {
                is ApiResult.Success -> {
                    fail("Should not be success for exception: ${exception.javaClass.simpleName}")
                }
                is ApiResult.Error -> {
                    // 模拟ViewModel中的错误消息映射
                    val userFriendlyMessage = when (result.code) {
                        500 -> "服务器内部错误，请稍后重试"
                        400 -> "图片格式不支持或文件过大"
                        401 -> "登录已过期，请重新登录"
                        403 -> "没有权限上传图片"
                        404 -> "上传服务不可用"
                        else -> result.message ?: "上传失败，请重试"
                    }
                    
                    assertEquals("User-friendly message should match for ${exception.javaClass.simpleName}", 
                        expectedMessage, userFriendlyMessage)
                    assertEquals("Error code should be preserved", 
                        exception.statusCode, result.code)
                    assertNotNull("Exception should be preserved", result.exception)
                }
            }
        }
    }

    @Test
    fun `test error propagation through multiple layers`() = runTest {
        // Given: 模拟多层调用中的错误传播
        val serverException = InternalServerException.builder()
            .statusCode(500)
            .body("Database connection failed")
            .build()

        // 模拟IntyNetworkManager.executeRequest抛出异常
        mockkObject(IntyNetworkManager)
        every { IntyNetworkManager.executeRequest(any<String>(), any(), any<suspend () -> String>()) } answers {
            val apiCall = thirdArg<suspend () -> String>()
            try {
                apiCall()
                ApiResult.Success("success")
            } catch (e: Exception) {
                e.toApiResult()
            }
        }

        // When: 模拟多层调用
        val result = IntyNetworkManager.executeRequest("Test Operation") {
            throw serverException
        }

        // Then: 验证错误传播
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        
        assertEquals("Error code should be preserved", 500, errorResult.code)
        assertEquals("Error message should be preserved", serverException.message, errorResult.message)
        assertEquals("Exception should be preserved", serverException, errorResult.exception)
    }

    @Test
    fun `test error handling with different exception types`() = runTest {
        // Given: 不同类型的异常
        val exceptions = listOf(
            InternalServerException.builder().statusCode(500).body("Server error").build(),
            RuntimeException("Runtime error"),
            IllegalArgumentException("Invalid argument"),
            IllegalStateException("Invalid state")
        )

        exceptions.forEach { exception ->
            // When: 转换为ApiResult
            val result: ApiResult<String> = exception.toApiResult()

            // Then: 验证处理结果
            assertTrue("Result should be Error for ${exception.javaClass.simpleName}", 
                result is ApiResult.Error)
            
            val errorResult = result as ApiResult.Error
            
            // 验证HTTP状态码映射
            val expectedCode = when (exception) {
                is InternalServerException -> 500
                else -> -1
            }
            
            assertEquals("HTTP code should match for ${exception.javaClass.simpleName}", 
                expectedCode, errorResult.code)
            assertEquals("Message should be preserved", 
                exception.message, errorResult.message)
            assertEquals("Exception should be preserved", 
                exception, errorResult.exception)
        }
    }

    @Test
    fun `test success case for comparison`() = runTest {
        // Given: 成功的API调用
        val mockApiResponse = mockk<ApiResponseDict>()
        val mockData = mockk<com.inty.api.models.api.v1.report.ApiResponseDictData>()
        
        every { mockApiResponse.data() } returns mockData
        every { mockData._additionalProperties() } returns mapOf("url" to "\"https://example.com/image.jpg\"")
        
        val mockApi = mockk<com.inty.api.services.blocking.api.V1Service>()
        val mockV1Api = mockk<com.inty.api.services.blocking.api.V1ServiceImpl>()
        
        every { mockIntyClient.api() } returns mockk {
            every { v1() } returns mockV1Api
        }
        
        every { mockV1Api.uploadImage(any<V1UploadImageParams>()) } returns mockApiResponse

        // When: 调用ImageService上传图片
        val testFilePath = "/test/path/image.jpg"
        val result = ImageService.uploadImage(testFilePath, croppingAvatar = true)

        // Then: 验证成功结果
        assertTrue("Result should be Success", result is ApiResult.Success)
        val successResult = result as ApiResult.Success<String>
        assertEquals("URL should be extracted", "https://example.com/image.jpg", successResult.data)
        
        // 验证成功日志
        verify { LogUtils.d("ImageService: Starting image upload - filePath: $testFilePath, croppingAvatar: true") }
        verify { LogUtils.d("ImageService: Received response from server") }
        verify { LogUtils.d("ImageService: Successfully extracted URL: https://example.com/image.jpg") }
    }

    @Test
    fun `test error handling with null message`() = runTest {
        // Given: 异常消息为null的情况
        val exception = InternalServerException.builder()
            .statusCode(500)
            .body("Server error")
            .build()
        
        // 模拟异常消息为null
        every { exception.message } returns null

        // When: 转换为ApiResult
        val result: ApiResult<String> = exception.toApiResult()

        // Then: 验证处理结果
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        
        assertEquals("Should use default message when exception message is null", 
            "Unknown error", errorResult.message)
        assertEquals("HTTP code should be preserved", 500, errorResult.code)
        assertEquals("Exception should be preserved", exception, errorResult.exception)
    }
}
