package com.ai.intellimate.utils

import ai.sxwl.android.data.billing.BillingErrorCode
import ai.sxwl.android.data.billing.BillingEvent
import ai.sxwl.android.utils.ToastUtils
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.ai.intellimate.testing.LogUtilsTestHelper
import io.mockk.Runs
import io.mockk.clearMocks
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject
import io.mockk.verify
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class BillingErrorHandlerTest {

    private val context: Context by lazy { ApplicationProvider.getApplicationContext() }

    @Before
    fun setUp() {
        LogUtilsTestHelper.mock()
        mockkObject(ToastUtils)
        every { ToastUtils.showShort(any<String>()) } just Runs
        clearMocks(ToastUtils)
    }

    @After
    fun tearDown() {
        unmockkObject(ToastUtils)
        LogUtilsTestHelper.unmock()
    }

    @Test
    fun handleShowError_userInitiatedDisplaysFormattedMessage() {
        val event =
            BillingEvent.ShowError(
                errorCode = BillingErrorCode.SUBSCRIPTION_VERIFICATION_FAILED,
                detailMessage = "Network glitch",
                isUserInitiated = true,
            )

        BillingErrorHandler.handleShowError(event, context)

        verify(exactly = 1) { ToastUtils.showShort("Subscription verification failed: Network glitch") }
    }

    @Test
    fun handleShowError_backgroundOperationSkipsToast() {
        val event =
            BillingEvent.ShowError(
                errorCode = BillingErrorCode.SUBSCRIPTION_VERIFICATION_FAILED,
                detailMessage = "Network glitch",
                isUserInitiated = false,
            )

        BillingErrorHandler.handleShowError(event, context)

        verify(exactly = 0) { ToastUtils.showShort(any<String>()) }
    }

    @Test
    fun handlePurchaseFailed_userInitiatedUsesBaseMessageWhenNoPlaceholder() {
        val event =
            BillingEvent.PurchaseFailed(
                errorCode = BillingErrorCode.PURCHASE_FAILED,
                billingResponseCode = -1,
                detailMessage = "ignored",
                isUserInitiated = true,
            )

        BillingErrorHandler.handlePurchaseFailed(event, context)

        verify(exactly = 1) { ToastUtils.showShort("Purchase failed. Please try again later") }
    }

    @Test
    fun handleSkuDetailsQueryFailed_userInitiatedFormatsDetail() {
        val event =
            BillingEvent.SkuDetailsQueryFailed(
                errorCode = BillingErrorCode.PRODUCT_DETAILS_QUERY_FAILED,
                billingResponseCode = -1,
                detailMessage = "sku-1",
                isUserInitiated = true,
            )

        BillingErrorHandler.handleSkuDetailsQueryFailed(event, context)

        verify(exactly = 1) { ToastUtils.showShort("Failed to load product details: sku-1") }
    }

    @Test
    fun handleBillingEvent_googlePlayServiceErrorWithoutActivityFallsBackToShowError() {
        val event =
            BillingEvent.GooglePlayServiceError(
                errorCode = BillingErrorCode.GOOGLE_PLAY_SERVICE_DISABLED,
                connectionResult = 1,
                isUserInitiated = true,
            )

        BillingErrorHandler.handleBillingEvent(event, context, activity = null)

        verify(exactly = 1) { ToastUtils.showShort("Google Play services are disabled") }
    }
}
