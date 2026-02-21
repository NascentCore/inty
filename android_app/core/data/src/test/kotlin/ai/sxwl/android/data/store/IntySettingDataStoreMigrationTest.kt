package ai.sxwl.android.data.store

import ai.sxwl.android.utils.Utils
import android.app.Application
import androidx.test.core.app.ApplicationProvider
import com.tencent.mmkv.MMKV
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

private const val TEST_KEY_TOKEN = "token"
private const val TEST_KEY_APP_DATA_PREFIX = "app_data_"

@RunWith(RobolectricTestRunner::class)
class IntySettingDataStoreMigrationTest {

    private lateinit var app: Application

    @Before
    fun setUp() {
        app = ApplicationProvider.getApplicationContext()
        Utils.init(app)
        MMKV.initialize(app)
    }

    @After
    fun tearDown() = Unit

    @Test
    fun getCurToken_migratesLegacyValueToDataStoreAndKeepsDataStoreAsSource() {
        val userId = "migration_user_${System.nanoTime()}"
        val userLegacyStore = legacyUserStore(userId)
        userLegacyStore.clearAll()

        IntySetting.changeUser(userId)
        userLegacyStore.putString(TEST_KEY_TOKEN, "legacy_token")

        assertEquals("legacy_token", IntySetting.getCurToken())

        userLegacyStore.putString(TEST_KEY_TOKEN, "legacy_token_changed")
        assertEquals("legacy_token", IntySetting.getCurToken())
    }

    @Test
    fun setToken_writesOnlyToDataStore() {
        val userId = "write_only_user_${System.nanoTime()}"
        val userLegacyStore = legacyUserStore(userId)
        userLegacyStore.clearAll()

        IntySetting.changeUser(userId)
        IntySetting.setToken("data_store_token")

        assertEquals("data_store_token", IntySetting.getCurToken())
        assertNull(userLegacyStore.decodeString(TEST_KEY_TOKEN))
    }

    @Test
    fun clearAppData_shouldNotFallBackToLegacyMmkvAgain() {
        val userId = "clear_app_data_user_${System.nanoTime()}"
        IntySetting.changeUser(userId)

        val appDataKey = "video_cache_${System.nanoTime()}"
        val legacyFullKey = "$TEST_KEY_APP_DATA_PREFIX$appDataKey"
        val allUserLegacyStore = legacyAllUserStore()
        allUserLegacyStore.removeValueForKey(legacyFullKey)
        allUserLegacyStore.putString(legacyFullKey, "/legacy/path.mp4")

        assertEquals("/legacy/path.mp4", IntySetting.getAppData(appDataKey))

        IntySetting.clearAppData(appDataKey)
        allUserLegacyStore.putString(legacyFullKey, "/legacy/new_path.mp4")

        assertNull(IntySetting.getAppData(appDataKey))
    }

    private fun legacyUserStore(userId: String): MMKV {
        return MMKV.mmkvWithID("user_$userId", MMKV.MULTI_PROCESS_MODE)
    }

    private fun legacyAllUserStore(): MMKV {
        return MMKV.defaultMMKV(MMKV.SINGLE_PROCESS_MODE, app.packageName)
    }
}
