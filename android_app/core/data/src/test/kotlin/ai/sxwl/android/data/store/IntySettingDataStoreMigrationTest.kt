package ai.sxwl.android.data.store

import ai.sxwl.android.utils.Utils
import android.app.Application
import androidx.test.core.app.ApplicationProvider
import com.tencent.mmkv.MMKV
import kotlinx.coroutines.runBlocking
import org.junit.Assume.assumeTrue
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

private const val TEST_DATASTORE_ALL_USER_NAME = "inty_setting_all_user"
private const val TEST_DATASTORE_USER_PREFIX = "inty_setting_user_"
private const val TEST_KEY_TOKEN = "token"
private const val TEST_KEY_APP_DATA_PREFIX = "app_data_"
private const val TEST_USER_ID_MIGRATION = "mmkv_migration_test_user"
private const val TEST_USER_ID_WRITE_ONLY = "mmkv_write_only_test_user"
private const val TEST_USER_ID_APP_DATA = "mmkv_app_data_test_user"
private const val TEST_APP_DATA_KEY = "video_cache_test_key"

@RunWith(RobolectricTestRunner::class)
class IntySettingDataStoreMigrationTest {

    private lateinit var app: Application

    @Before
    fun setUp() {
        app = ApplicationProvider.getApplicationContext()
        Utils.init(app)
        assumeTrue("MMKV is not available in current unit test runtime", initializeMmkvCompat(app))
        cleanupTestData()
    }

    @After
    fun tearDown() {
        cleanupTestData()
    }

    @Test
    fun getCurToken_migratesLegacyValueToDataStoreAndKeepsDataStoreAsSource() {
        val userLegacyStore = legacyUserStore(TEST_USER_ID_MIGRATION)
        userLegacyStore.clearAll()

        IntySetting.changeUser(TEST_USER_ID_MIGRATION)
        userLegacyStore.putString(TEST_KEY_TOKEN, "legacy_token")

        assertEquals("legacy_token", IntySetting.getCurToken())

        userLegacyStore.putString(TEST_KEY_TOKEN, "legacy_token_changed")
        assertEquals("legacy_token", IntySetting.getCurToken())
    }

    @Test
    fun setToken_writesOnlyToDataStore() {
        val userLegacyStore = legacyUserStore(TEST_USER_ID_WRITE_ONLY)
        userLegacyStore.clearAll()

        IntySetting.changeUser(TEST_USER_ID_WRITE_ONLY)
        IntySetting.setToken("data_store_token")

        assertEquals("data_store_token", IntySetting.getCurToken())
        assertNull(userLegacyStore.decodeString(TEST_KEY_TOKEN))
    }

    @Test
    fun clearAppData_shouldNotFallBackToLegacyMmkvAgain() {
        IntySetting.changeUser(TEST_USER_ID_APP_DATA)

        val appDataKey = TEST_APP_DATA_KEY
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

    private fun cleanupTestData() {
        runBlocking {
            dataStore(TEST_DATASTORE_ALL_USER_NAME).clear()
            dataStore("$TEST_DATASTORE_USER_PREFIX$TEST_USER_ID_MIGRATION").clear()
            dataStore("$TEST_DATASTORE_USER_PREFIX$TEST_USER_ID_WRITE_ONLY").clear()
            dataStore("$TEST_DATASTORE_USER_PREFIX$TEST_USER_ID_APP_DATA").clear()
        }

        legacyUserStore(TEST_USER_ID_MIGRATION).clearAll()
        legacyUserStore(TEST_USER_ID_WRITE_ONLY).clearAll()
        legacyUserStore(TEST_USER_ID_APP_DATA).clearAll()
        legacyAllUserStore().removeValueForKey("$TEST_KEY_APP_DATA_PREFIX$TEST_APP_DATA_KEY")
    }

    private fun initializeMmkvCompat(application: Application): Boolean {
        val mmkvClass = MMKV::class.java

        val initWithContextSucceeded =
            runCatching {
                    mmkvClass.getMethod("initialize", android.content.Context::class.java)
                        .invoke(null, application)
                }
                .isSuccess
        if (initWithContextSucceeded) return true

        val initWithPathSucceeded =
            runCatching {
                    mmkvClass.getMethod("initialize", String::class.java)
                        .invoke(null, application.filesDir.resolve("mmkv").absolutePath)
                }
                .isSuccess
        if (initWithPathSucceeded) return true

        val initWithPathAndLevelSucceeded =
            runCatching {
                    val logLevelClass = Class.forName("com.tencent.mmkv.MMKVLogLevel")
                    val level = logLevelClass.enumConstants.firstOrNull()
                    if (level != null) {
                        mmkvClass.getMethod("initialize", String::class.java, logLevelClass)
                            .invoke(null, application.filesDir.resolve("mmkv").absolutePath, level)
                    } else {
                        error("MMKVLogLevel enum is empty")
                    }
                }
                .isSuccess
        return initWithPathAndLevelSucceeded
    }
}
