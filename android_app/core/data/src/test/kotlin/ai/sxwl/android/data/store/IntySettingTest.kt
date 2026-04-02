package ai.sxwl.android.data.store

import android.content.Context
import android.os.Build
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.flow.first
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

/**
 * IntySetting 单元测试。
 *
 * 使用 Robolectric 提供 Context，在 @Before 中通过 resetCacheForTest 将 DataStore 置为已迁移状态， 避免 initialize 触发
 * MMKV 迁移（MMKV 需真机/模拟器）。测试覆盖由 intySettingsCache 支撑的读写行为。
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [Build.VERSION_CODES.P])
class IntySettingTest {

    private lateinit var context: Context

    @Before
    fun setUp() {
        context = RuntimeEnvironment.getApplication()
        IntySetting.resetCacheForTest(context)
        IntySetting.initialize(context)
    }

    @Test
    fun getCurUserID_beforeChangeUser_returnsEmpty() {
        assertEquals("", IntySetting.getCurUserID())
    }

    @Test
    fun getCurToken_beforeSet_returnsEmpty() {
        assertEquals("", IntySetting.getCurToken())
    }

    @Test
    fun isLogin_beforeLogin_returnsFalse() {
        assertFalse(IntySetting.isLogin())
    }

    @Test
    fun changeUser_and_setToken_then_gettersReturnValues() = runBlocking {
        IntySetting.changeUser("uid-1")
        IntySetting.setToken("token-1")

        assertEquals("uid-1", IntySetting.getCurUserID())
        assertEquals("token-1", IntySetting.getCurToken())
        assertTrue(IntySetting.isLogin())
    }

    @Test
    fun setKeyboardHeight_then_keyboardHeightFlow_returnsValue() = runBlocking {
        IntySetting.setKeyboardHeight(256f)
        assertEquals(256f, IntySetting.keyboardHeightFlow().first(), 0f)
    }

    @Test
    fun hasUserSetKeepTalking_default_returnsFalse() {
        assertFalse(runBlocking { IntySetting.hasUserSetKeepTalking() })
    }

    @Test
    fun markUserSetKeepTalking_then_hasUserSetKeepTalking_returnsTrue() = runBlocking {
        IntySetting.markUserSetKeepTalking()
        assertTrue(IntySetting.hasUserSetKeepTalking())
    }

    @Test
    fun setVibeModeEnabled_then_isVibeModeEnabled_returnsValue() {
        IntySetting.setVibeModeEnabled(true)
        assertTrue(IntySetting.isVibeModeEnabled())
        IntySetting.setVibeModeEnabled(false)
        assertFalse(IntySetting.isVibeModeEnabled())
    }

    @Test
    fun setTipsDisabled_then_isTipsDisabled_returnsValue() {
        IntySetting.setTipsDisabled(true)
        assertTrue(IntySetting.isTipsDisabled())
        IntySetting.setTipsDisabled(false)
        assertFalse(IntySetting.isTipsDisabled())
    }

    @Test
    fun setLastResubReminderDialogShowTime_then_getReturnsValue() = runBlocking {
        IntySetting.setLastResubReminderDialogShowTime(999L)
        assertEquals(999L, IntySetting.getLastResubReminderDialogShowTime())
    }

    @Test
    fun setResubReminderDialogShowCount_then_getReturnsValue() = runBlocking {
        IntySetting.setResubReminderDialogShowCount(3)
        assertEquals(3, IntySetting.getResubReminderDialogShowCount())
    }

    @Test
    fun setFeedbackDialogLastShowTime_then_getReturnsValue() = runBlocking {
        IntySetting.setFeedbackDialogLastShowTime(2000L)
        assertEquals(2000L, IntySetting.getFeedbackDialogLastShowTime())
    }

    @Test
    fun setMessagesTabHasPush_then_hasMessagesTabPush_returnsValue() = runBlocking {
        IntySetting.setMessagesTabHasPushSuspend(true)
        assertTrue(IntySetting.hasMessagesTabPush())
        IntySetting.setMessagesTabHasPushSuspend(false)
        assertFalse(IntySetting.hasMessagesTabPush())
    }

    @Test
    fun setConversationHasPush_then_hasConversationPush_returnsValue() = runBlocking {
        IntySetting.setConversationHasPush("agent-a", true)
        assertTrue(IntySetting.hasConversationPush("agent-a"))
        IntySetting.setConversationHasPush("agent-a", false)
        assertFalse(IntySetting.hasConversationPush("agent-a"))
    }

    @Test
    fun setAppUpdateTips_then_hasAppUpdateTips_returnsValue() = runBlocking {
        IntySetting.setAppUpdateTips(true)
        assertTrue(IntySetting.hasAppUpdateTips())
        IntySetting.setAppUpdateTips(false)
        assertFalse(IntySetting.hasAppUpdateTips())
    }

    @Test
    fun setUserProfileData_then_getUserProfileData_returnsValue() = runBlocking {
        IntySetting.setUserProfileData("key1", "value1")
        assertEquals("value1", IntySetting.getUserProfileData("key1"))
        IntySetting.clearUserProfileData("key1")
        assertEquals(null, IntySetting.getUserProfileData("key1"))
    }

    @Test
    fun setShowGuested_then_hasShowGuest_returnsTrue() = runBlocking {
        IntySetting.setShowGuested()
        assertTrue(IntySetting.hasShowGuest())
    }

    @Test
    fun setAppData_getAppData_clearAppData_getAllAppDataKeys() = runBlocking {
        IntySetting.setAppData("k1", "v1")
        IntySetting.setAppData("k2", "v2")
        assertEquals("v1", IntySetting.getAppData("k1"))
        assertEquals("v2", IntySetting.getAppData("k2"))
        assertTrue(IntySetting.getAllAppDataKeys().containsAll(setOf("k1", "k2")))
        IntySetting.clearAppData("k1")
        assertEquals(null, IntySetting.getAppData("k1"))
        assertEquals("v2", IntySetting.getAppData("k2"))
    }

    @Test
    fun setExploreAgentFavorite_then_isExploreAgentFavorite_and_getExploreFavoriteAgentIds() =
        runBlocking {
            IntySetting.setExploreAgentFavorite("agent-x", true)
            IntySetting.setExploreAgentFavorite("agent-y", true)
            assertTrue(IntySetting.isExploreAgentFavorite("agent-x"))
            assertTrue(IntySetting.isExploreAgentFavorite("agent-y"))
            val ids = IntySetting.getExploreFavoriteAgentIds()
            assertTrue(ids.contains("agent-x"))
            assertTrue(ids.contains("agent-y"))
            IntySetting.setExploreAgentFavorite("agent-x", false)
            assertFalse(IntySetting.isExploreAgentFavorite("agent-x"))
            assertTrue(IntySetting.isExploreAgentFavorite("agent-y"))
        }

    @Test
    fun setChatBackgroundImage_getChatBackgroundImage_clearChatBackgroundImage() = runBlocking {
        IntySetting.setChatBackgroundImage("agent-bg", "https://example.com/bg.png")
        assertEquals("https://example.com/bg.png", IntySetting.getChatBackgroundImage("agent-bg"))
        IntySetting.clearChatBackgroundImage("agent-bg")
        assertEquals(null, IntySetting.getChatBackgroundImage("agent-bg"))
    }

    @Test
    fun setConversationPinned_then_isConversationPinned_returnsValue() = runBlocking {
        IntySetting.setConversationPinned("agent-pin", true)
        assertTrue(IntySetting.isConversationPinned("agent-pin"))
        IntySetting.setConversationPinned("agent-pin", false)
        assertFalse(IntySetting.isConversationPinned("agent-pin"))
    }

    @Test
    fun setConversationHidden_then_isConversationHidden_and_getConversationHiddenTime() =
        runBlocking {
            IntySetting.setConversationHidden("agent-hide", true)
            assertTrue(IntySetting.isConversationHidden("agent-hide"))
            assertTrue(IntySetting.getConversationHiddenTime("agent-hide") > 0L)
            IntySetting.setConversationHidden("agent-hide", false)
            assertFalse(IntySetting.isConversationHidden("agent-hide"))
            assertEquals(0L, IntySetting.getConversationHiddenTime("agent-hide"))
        }

    @Test
    fun updateSortSeed_then_sortSeed_returnsValue() = runBlocking {
        IntySetting.updateSortSeed(42)
        assertEquals(42, IntySetting.sortSeed())
    }

    @Test
    fun logout_clearsToken_and_isLoginReturnsFalse() = runBlocking {
        IntySetting.changeUser("uid-2")
        IntySetting.setToken("token-2")
        assertTrue(IntySetting.isLogin())

        IntySetting.logout()
        assertEquals("", IntySetting.getCurToken())
        assertFalse(IntySetting.isLogin())
    }
}
