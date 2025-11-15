package ai.sxwl.android.data.billing

import org.junit.Assert.assertEquals
import org.junit.Test

class BillingUtilsTest {

    @Test
    fun correctCurrencySymbol_returnsFormattedUsdPrice() {
        val result = BillingUtils.correctCurrencySymbol("\$10.00", "USD")

        assertEquals("\$10", result)
    }
}
