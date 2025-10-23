package com.ai.inty

import com.ai.inty.utils.NetworkErrorHandler
import org.junit.Assert
import org.junit.Test

class NetworkErrorHandlerTest {

    private data class TestCase(
        val exceptionMessage: String,
        val expectedMessage: String,
        val description: String,
    )

    private val testCases =
        listOf(
            TestCase(
                "Request timeout after 30 seconds",
                "Request timeout, please try again later",
                "timeout exception",
            ),
            TestCase(
                "Network connection failed",
                "Network connection failed, please check your network settings",
                "network exception",
            ),
            TestCase(
                "Connection refused",
                "Connection failed, please check your network settings",
                "connection exception",
            ),
            TestCase(
                "Invalid JSON format",
                "Data format error, please try again later",
                "JSON exception",
            ),
            TestCase(
                "Daily image generation limit reached (4/4)",
                "Daily image generation limit reached (4/4)",
                "daily limit exception (preserves original message)",
            ),
            TestCase(
                "Some random error occurred",
                "Network request failed",
                "unknown exception (generic fallback)",
            ),
        )

    @Test
    fun handleNetworkException_withVariousExceptions_returnsFormattedMessages() {
        println("🧪 Testing multiple exception scenarios with parameterized approach")

        testCases.forEach { testCase ->
            println("  Testing: ${testCase.description}")

            val exception = Exception(testCase.exceptionMessage)
            var capturedMessage = ""
            val showToast: (String) -> Unit = { message -> capturedMessage = message }

            NetworkErrorHandler.handleNetworkException(
                isNetworkConnected = true,
                exception = exception,
                showToast = showToast,
                logError = false,
            )

            Assert.assertEquals(
                "Failed for: ${testCase.description}",
                testCase.expectedMessage,
                capturedMessage,
            )
        }
    }

    @Test
    fun handleNetworkException_withNoNetwork_returnsEmptyMessage() {
        println("🧪 Testing no network scenario!")

        val timeoutException = Exception("Request timeout after 30 seconds")
        var capturedMessage = ""
        val showToast: (String) -> Unit = { message -> capturedMessage = message }

        NetworkErrorHandler.handleNetworkException(
            isNetworkConnected = false,
            exception = timeoutException,
            showToast = showToast,
            logError = false,
        )

        Assert.assertEquals("", capturedMessage)
    }
}
