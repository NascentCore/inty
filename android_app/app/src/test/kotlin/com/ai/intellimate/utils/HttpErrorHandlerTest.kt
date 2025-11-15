package com.ai.intellimate.utils

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

class HttpErrorHandlerTest {

    @Test
    fun handleHttpException_mapsStatusCodesToUserFriendlyMessages() {
        val agentNotFound =
            HttpErrorHandler.handleHttpException(httpException(404), operation = "agent lookup")
        val throttled =
            HttpErrorHandler.handleHttpException(httpException(429), operation = "any")

        assertEquals("Character not found", agentNotFound)
        assertEquals("Too many requests, please try again later", throttled)
    }

    @Test
    fun handleGeneralException_detectsKeywordHintsOrPrefixesOperation() {
        val timeoutMessage =
            HttpErrorHandler.handleGeneralException(Exception("Timeout while waiting"))
        val networkMessage =
            HttpErrorHandler.handleGeneralException(Exception("network unavailable"))
        val createFailure =
            HttpErrorHandler.handleGeneralException(Exception("boom"), operation = "create agent")

        assertEquals("Request timeout, please try again later", timeoutMessage)
        assertEquals("Network connection failed, please check your connection", networkMessage)
        assertEquals("Creation failed: boom", createFailure)
    }

    private fun httpException(code: Int): HttpException {
        val response =
            Response.error<String>(
                code,
                "error".toResponseBody("application/json".toMediaType()),
            )
        return HttpException(response)
    }
}
