package ai.sxwl.android.data.http

import ai.sxwl.android.data.http.services.ImageService
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import com.inty.api.errors.InternalServerException
import com.inty.api.errors.BadRequestException
import com.inty.api.errors.UnauthorizedException
import com.inty.api.errors.NotFoundException
import io.mockk.*
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import java.io.File
import java.nio.file.Paths

/**
 * 测试HTTP 500错误处理行为
 * 
 * 这个测试展示了：
 * 1. ApiResult如何包装不同类型的异常
 * 2. HTTP状态码的正确映射
 * 3. 错误信息的详细记录
 * 4. 异常到ApiResult的转换过程
 */
class Http500ErrorHandlingTest {

    @Before
    fun setup() {
        // 模拟LogUtils，避免实际日志输出
        mockkStatic(LogUtils::class)
        every { LogUtils.e(any<String>()) } just Runs
        every { LogUtils.e(any<String>(), any<Throwable>()) } just Runs
        every { LogUtils.d(any<String>()) } just Runs
        every { LogUtils.i(any<String>()) } just Runs
        
        // 模拟NetworkConfig
        mockkObject(NetworkConfig)
        every { NetworkConfig.shouldEnableDetailedLogging() } returns true
    }

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
        
        // 验证日志记录
        verify { LogUtils.e("API exception: ${serverException.message}") }
        verify { LogUtils.e("API exception type: InternalServerException") }
        verify { LogUtils.e("API exception HTTP code: 500") }
    }

    @Test
    fun `test BadRequestException converts to 400 error`() = runTest {
        // Given: 模拟400客户端请求错误
        val badRequestException = BadRequestException.builder()
            .statusCode(400)
            .body("{\"code\":400,\"message\":\"Bad request\"}")
            .build()

        // When: 将异常转换为ApiResult
        val result: ApiResult<String> = badRequestException.toApiResult()

        // Then: 验证结果
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        
        assertEquals("HTTP code should be 400", 400, errorResult.code)
        assertEquals("Message should match exception", badRequestException.message, errorResult.message)
        assertEquals("Exception should be preserved", badRequestException, errorResult.exception)
        
        verify { LogUtils.e("API exception HTTP code: 400") }
    }

    @Test
    fun `test UnauthorizedException converts to 401 error`() = runTest {
        // Given: 模拟401未授权错误
        val unauthorizedException = UnauthorizedException.builder()
            .statusCode(401)
            .body("{\"code\":401,\"message\":\"Unauthorized\"}")
            .build()

        // When: 将异常转换为ApiResult
        val result: ApiResult<String> = unauthorizedException.toApiResult()

        // Then: 验证结果
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        
        assertEquals("HTTP code should be 401", 401, errorResult.code)
        assertEquals("Message should match exception", unauthorizedException.message, errorResult.message)
        assertEquals("Exception should be preserved", unauthorizedException, errorResult.exception)
        
        verify { LogUtils.e("API exception HTTP code: 401") }
    }

    @Test
    fun `test NotFoundException converts to 404 error`() = runTest {
        // Given: 模拟404资源未找到错误
        val notFoundException = NotFoundException.builder()
            .statusCode(404)
            .body("{\"code\":404,\"message\":\"Not found\"}")
            .build()

        // When: 将异常转换为ApiResult
        val result: ApiResult<String> = notFoundException.toApiResult()

        // Then: 验证结果
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        
        assertEquals("HTTP code should be 404", 404, errorResult.code)
        assertEquals("Message should match exception", notFoundException.message, errorResult.message)
        assertEquals("Exception should be preserved", notFoundException, errorResult.exception)
        
        verify { LogUtils.e("API exception HTTP code: 404") }
    }

    @Test
    fun `test unknown exception converts to -1 error code`() = runTest {
        // Given: 模拟未知异常
        val unknownException = RuntimeException("Unknown error occurred")

        // When: 将异常转换为ApiResult
        val result: ApiResult<String> = unknownException.toApiResult()

        // Then: 验证结果
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        
        assertEquals("HTTP code should be -1 for unknown exceptions", -1, errorResult.code)
        assertEquals("Message should match exception", unknownException.message, errorResult.message)
        assertEquals("Exception should be preserved", unknownException, errorResult.exception)
        
        verify { LogUtils.e("API exception HTTP code: -1") }
    }

    @Test
    fun `test executeApiCall with success`() = runTest {
        // Given: 成功的API调用
        val expectedData = "test data"
        val apiCall: suspend () -> String = { expectedData }

        // When: 执行API调用
        val result: ApiResult<String> = executeApiCall(apiCall)

        // Then: 验证结果
        assertTrue("Result should be Success", result is ApiResult.Success)
        val successResult = result as ApiResult.Success<String>
        assertEquals("Data should match", expectedData, successResult.data)
    }

    @Test
    fun `test executeApiCall with exception`() = runTest {
        // Given: 抛出异常的API调用
        val exception = InternalServerException.builder()
            .statusCode(500)
            .body("{\"code\":500,\"message\":\"Server error\"}")
            .build()
        val apiCall: suspend () -> String = { throw exception }

        // When: 执行API调用
        val result: ApiResult<String> = executeApiCall(apiCall)

        // Then: 验证结果
        assertTrue("Result should be Error", result is ApiResult.Error)
        val errorResult = result as ApiResult.Error
        assertEquals("HTTP code should be 500", 500, errorResult.code)
        assertEquals("Exception should be preserved", exception, errorResult.exception)
    }

    @Test
    fun `test ApiResult Success behavior`() = runTest {
        // Given: 成功的数据
        val testData = "success data"

        // When: 创建Success结果
        val result = ApiResult.Success(testData)

        // Then: 验证结果
        assertEquals("Data should match", testData, result.data)
        assertTrue("Should be Success type", result is ApiResult.Success)
        assertFalse("Should not be Error type", result is ApiResult.Error)
    }

    @Test
    fun `test ApiResult Error behavior`() = runTest {
        // Given: 错误信息
        val errorCode = 500
        val errorMessage = "Internal server error"
        val exception = RuntimeException("Test exception")

        // When: 创建Error结果
        val result = ApiResult.Error(errorCode, errorMessage, exception)

        // Then: 验证结果
        assertEquals("Code should match", errorCode, result.code)
        assertEquals("Message should match", errorMessage, result.message)
        assertEquals("Exception should match", exception, result.exception)
        assertTrue("Should be Error type", result is ApiResult.Error)
        assertFalse("Should not be Success type", result is ApiResult.Success)
    }

    @Test
    fun `test pattern matching with when expression`() = runTest {
        // Given: 不同类型的ApiResult
        val successResult: ApiResult<String> = ApiResult.Success("test")
        val errorResult: ApiResult<String> = ApiResult.Error(500, "Server error")

        // When & Then: 测试模式匹配
        val successHandled = when (successResult) {
            is ApiResult.Success -> {
                assertEquals("Should handle success", "test", successResult.data)
                true
            }
            is ApiResult.Error -> false
        }
        assertTrue("Success should be handled", successHandled)

        val errorHandled = when (errorResult) {
            is ApiResult.Success -> false
            is ApiResult.Error -> {
                assertEquals("Should handle error", 500, errorResult.code)
                assertEquals("Should handle error message", "Server error", errorResult.message)
                true
            }
        }
        assertTrue("Error should be handled", errorHandled)
    }

    @Test
    fun `test error handling in ViewModel context`() = runTest {
        // Given: 模拟ViewModel中的错误处理场景
        val serverError = InternalServerException.builder()
            .statusCode(500)
            .body("{\"code\":500,\"message\":\"Database connection failed\"}")
            .build()

        // When: 模拟ImageService调用失败
        val result: ApiResult<String> = serverError.toApiResult()

        // Then: 验证ViewModel如何处理错误
        when (result) {
            is ApiResult.Success -> {
                fail("Should not be success")
            }
            is ApiResult.Error -> {
                // 验证错误码映射
                val errorMessage = when (result.code) {
                    500 -> "服务器内部错误，请稍后重试"
                    400 -> "图片格式不支持或文件过大"
                    401 -> "登录已过期，请重新登录"
                    403 -> "没有权限上传图片"
                    404 -> "上传服务不可用"
                    else -> result.message ?: "上传失败，请重试"
                }
                
                assertEquals("Should map to user-friendly message", 
                    "服务器内部错误，请稍后重试", errorMessage)
                assertEquals("Should preserve original error code", 500, result.code)
                assertNotNull("Should preserve exception", result.exception)
            }
        }
    }

    @Test
    fun `test error logging behavior`() = runTest {
        // Given: 一个异常
        val exception = InternalServerException.builder()
            .statusCode(500)
            .body("{\"code\":500,\"message\":\"Test error\"}")
            .build()

        // When: 转换为ApiResult
        exception.toApiResult<String>()

        // Then: 验证日志记录
        verify { LogUtils.e("API exception: ${exception.message}") }
        verify { LogUtils.e("API exception type: InternalServerException") }
        verify { LogUtils.e("API exception stack trace:", exception) }
        verify { LogUtils.e("API exception HTTP code: 500") }
    }
}
