package ai.sxwl.android.data.store

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Instrumented tests for [IntySettingsDataStore]: defaults, read-after-write, user isolation.
 * Requires running with an Application that has initialized Utils (e.g. app process or test app).
 */
@RunWith(AndroidJUnit4::class)
class IntySettingsDataStoreTest {

    private val uidA = "test_uid_a_${System.nanoTime()}"
    private val uidB = "test_uid_b_${System.nanoTime()}"

    @After
    fun tearDown() {
        IntySettingsDataStore.onUserChanged()
    }

    @Test
    fun getChatFontSizeSp_returnsDefaultWhenNeverWritten() {
        assertEquals(14f, IntySettingsDataStore.getChatFontSizeSp(uidA), 0f)
    }

    @Test
    fun getChatModelId_returnsDefaultWhenNeverWritten() {
        assertEquals("gemini_3_flash", IntySettingsDataStore.getChatModelId(uidA))
    }

    @Test
    fun getBooleanSettings_returnDefaultsWhenNeverWritten() {
        assertFalse(IntySettingsDataStore.getChatListFullScreen(uidA))
        assertTrue(IntySettingsDataStore.getAutoPlayAnimation(uidA))
        assertTrue(IntySettingsDataStore.getTextStreaming(uidA))
        assertFalse(IntySettingsDataStore.getShowSceneActionButton(uidA))
        assertFalse(IntySettingsDataStore.getShowKeepTalking(uidA))
        assertTrue(IntySettingsDataStore.getAutoPlayAudio(uidA))
    }

    @Test
    fun setThenGetChatFontSizeSp_persistsValue() {
        IntySettingsDataStore.setChatFontSizeSp(uidA, 18f)
        assertEquals(18f, IntySettingsDataStore.getChatFontSizeSp(uidA), 0f)
    }

    @Test
    fun setThenGetChatModelId_persistsValue() {
        IntySettingsDataStore.setChatModelId(uidA, "custom_model")
        assertEquals("custom_model", IntySettingsDataStore.getChatModelId(uidA))
    }

    @Test
    fun setThenGetBoolean_persistsValue() {
        IntySettingsDataStore.setChatListFullScreen(uidA, true)
        assertTrue(IntySettingsDataStore.getChatListFullScreen(uidA))
        IntySettingsDataStore.setAutoPlayAudio(uidA, false)
        assertFalse(IntySettingsDataStore.getAutoPlayAudio(uidA))
    }

    @Test
    fun userIsolation_uidAAndUidBHaveIndependentValues() {
        IntySettingsDataStore.setChatFontSizeSp(uidA, 16f)
        IntySettingsDataStore.setChatModelId(uidA, "model_a")
        IntySettingsDataStore.setChatFontSizeSp(uidB, 12f)
        IntySettingsDataStore.setChatModelId(uidB, "model_b")

        assertEquals(16f, IntySettingsDataStore.getChatFontSizeSp(uidA), 0f)
        assertEquals("model_a", IntySettingsDataStore.getChatModelId(uidA))
        assertEquals(12f, IntySettingsDataStore.getChatFontSizeSp(uidB), 0f)
        assertEquals("model_b", IntySettingsDataStore.getChatModelId(uidB))
    }

    @Test
    fun onUserChanged_invalidatesCacheNextGetLoadsFromStore() {
        IntySettingsDataStore.setShowKeepTalking(uidA, true)
        assertTrue(IntySettingsDataStore.getShowKeepTalking(uidA))
        IntySettingsDataStore.onUserChanged()
        assertTrue(IntySettingsDataStore.getShowKeepTalking(uidA))
    }
}
