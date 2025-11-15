package com.ai.intellimate.utils

import ai.sxwl.android.utils.ToastUtils
import com.ai.intellimate.testing.LogUtilsTestHelper
import io.mockk.Runs
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject
import io.mockk.verify
import kotlinx.coroutines.CancellationException
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class NetworkErrorHandlerTest {

    @Before
    fun setUp() {
        LogUtilsTestHelper.mock()
        mockkObject(ToastUtils)
        every { ToastUtils.showShort(any<String>()) } just Runs
    }

    @After
    fun tearDown() {
        unmockkObject(ToastUtils)
        LogUtilsTestHelper.unmock()
    }

    @Test
    fun showNetworkAwareError_skipsCancelledMessages() {
        NetworkErrorHandler.showNetworkAwareError("Request cancelled by user")

        verify(exactly = 0) { ToastUtils.showShort(any<String>()) }
    }

    @Test
    fun showNetworkAwareError_displaysToastForOtherErrors() {
        NetworkErrorHandler.showNetworkAwareError("Server unavailable")

        verify(exactly = 1) { ToastUtils.showShort("Server unavailable") }
    }

    @Test
    fun handleNetworkException_returnsCancellationMessageWithoutToast() {
        val message =
            NetworkErrorHandler.handleNetworkException(CancellationException("cancel"))

        assertEquals("Request cancelled", message)
        verify(exactly = 0) { ToastUtils.showShort(any<String>()) }
    }

    @Test
    fun handleNetworkException_showsToastForGenericError() {
        val message = NetworkErrorHandler.handleNetworkException(Exception("Network down"))

        assertEquals("Network down", message)
        verify(exactly = 1) { ToastUtils.showShort("Network down") }
    }
}
