package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.ChatImageGenerationApiResponse
import ai.sxwl.android.data.api.model.ChatImageGenerationPayload
import ai.sxwl.android.data.http.BusinessErrorCodes
import com.architecture.httplib.core.HttpResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class ChatRemoteDataSourceImageMappingTest {
    private val dataSource = ChatRemoteDataSource()

    @Test
    fun mapGenerateImageResponse_returnsSuccess_whenCodeIs200AndPayloadIsValid() {
        val response =
            ChatImageGenerationApiResponse(
                code = 200,
                message = "success",
                data =
                    ChatImageGenerationPayload(
                        imageUrl = "https://example.com/image.webp",
                        imageMetadata = mapOf("width" to 1024, "height" to "768"),
                        messageId = 12345L,
                    ),
            )

        val result = dataSource.mapGenerateImageResponse("999", response)
        when (result) {
            is HttpResult.Success -> {
                assertEquals("https://example.com/image.webp", result.data.imageUrl)
                assertEquals(1024, result.data.width)
                assertEquals(768, result.data.height)
                assertEquals(12345L, result.data.messageId)
            }

            is HttpResult.Failure -> {
                fail("Expected success but got failure: ${result.code}, ${result.message}")
            }
        }
    }

    @Test
    fun mapGenerateImageResponse_returnsMappedBusinessCode_whenCodeMissingButErrorCodeExists() {
        val response =
            ChatImageGenerationApiResponse(
                code = null,
                message = "outer message",
                data =
                    ChatImageGenerationPayload(
                        errorCode = BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_ERROR_CODE,
                        message = "Image generation limit reached",
                    ),
            )

        val result = dataSource.mapGenerateImageResponse("100", response)
        when (result) {
            is HttpResult.Success -> {
                fail("Expected failure but got success")
            }

            is HttpResult.Failure -> {
                assertEquals(BusinessErrorCodes.IMAGE_GENERATION_LIMIT_REACHED_CODE, result.code)
                assertEquals("Image generation limit reached", result.message)
            }
        }
    }

    @Test
    fun mapGenerateImageResponse_returnsFailure_whenPayloadMissingImageUrl() {
        val response =
            ChatImageGenerationApiResponse(
                code = 200,
                message = "success",
                data = ChatImageGenerationPayload(imageUrl = null),
            )

        val result = dataSource.mapGenerateImageResponse("200", response)
        when (result) {
            is HttpResult.Success -> fail("Expected failure but got success")
            is HttpResult.Failure -> {
                assertEquals(-1, result.code)
                assertEquals("Image generation response is empty", result.message)
            }
        }
    }

    @Test
    fun mapGenerateImageResponse_returnsFailure_whenCodeMissingAndNoBusinessErrorCode() {
        val response =
            ChatImageGenerationApiResponse(
                code = null,
                message = "response code missing",
                data = ChatImageGenerationPayload(),
            )

        val result = dataSource.mapGenerateImageResponse("300", response)
        assertTrue(result is HttpResult.Failure)
        if (result is HttpResult.Failure) {
            assertEquals(-1, result.code)
            assertEquals("response code missing", result.message)
        }
    }
}
