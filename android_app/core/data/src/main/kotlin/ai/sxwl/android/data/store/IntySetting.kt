package ai.sxwl.android.data.store

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.utils.AppUtils
import android.os.Handler
import android.os.Looper
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import com.tencent.mmkv.MMKV
import kotlin.random.Random
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

private const val KEY_RESUB_REMINDER_LAST_TIME = "resub_reminder_last_time"
private const val KEY_RESUB_REMINDER_SHOW_COUNT = "resub_reminder_show_count"
private const val KEY_CHAT_FONT_SIZE_SP = "chat_font_size_sp"
private const val KEY_CHAT_MODEL_ID = "chat_model_id"
private const val KEY_MESSAGES_TAB_HAS_PUSH = "messages_tab_has_push"
private const val KEY_CONVERSATION_PUSH_PREFIX = "conversation_has_push_"
private const val DEFAULT_CHAT_FONT_SIZE_SP = 14f
private const val DEFAULT_CHAT_MODEL_ID = "gemini_3_flash"
private const val KEY_PREFIX_EXPLORE_FAVORITE = "explore_favorite_"
private const val KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME = "feedback_dialog_last_show_time"
private const val KEY_TOTAL_MESSAGE_COUNT = "total_message_count"
private const val KEY_INTELLIMATE_TIP_LAST_SHOW_TIME = "intellimate_tip_last_show_time"
private const val KEY_CONVERSATION_PINNED_PREFIX = "conversation_pinned_"
private const val KEY_CONVERSATION_HIDDEN_PREFIX = "conversation_hidden_"
private const val KEY_CONVERSATION_HIDDEN_TIME_PREFIX = "conversation_hidden_time_"
private const val KEY_USER_PROFILE_PREFIX = "user_profile_"
private const val KEY_APP_DATA_PREFIX = "app_data_"
private const val KEY_CHAT_MESSAGES_PREFIX = "chat_messages_"
private const val KEY_CHAT_OFFSET_PREFIX = "chat_offset_"
private const val KEY_CHAT_HAS_MORE_PREFIX = "chat_has_more_"
private const val KEY_CHAT_INITIAL_LOADED_PREFIX = "chat_initial_loaded_"
private const val KEY_CURRENT_USER_ID = "cur_uid"
private const val KEY_TOKEN = "token"
private const val KEY_KEYBOARD_HEIGHT = "keyboardHeight"
private const val KEY_SHOW_GUEST = "show_guest"
private const val KEY_APP_UPDATE_TIPS = "has_app_update_tips"
private const val KEY_SORT_SEED = "current_sort_seed"
private const val DATASTORE_ALL_USER_NAME = "inty_setting_all_user"
private const val DATASTORE_USER_PREFIX = "inty_setting_user_"
private const val LEGACY_MIGRATION_MARK_PREFIX = "__legacy_migrated__"

// IntelliMate Tips 展示频率：最多每 8 小时一次（降低打扰）
private const val INTELLIMATE_TIP_MIN_INTERVAL_MILLIS = 8 * 60 * 60 * 1000L

object IntySetting {

    // App 级 DataStore（所有用户共享）
    private val allUserDataStore: DataStore<Preferences> = dataStore(DATASTORE_ALL_USER_NAME)

    // 仅用于迁移读取，业务读写全部走 DataStore
    // MMKV.initialize(app) 已经在 IntelliMateApp.onCreate() 中调用
    private val allUserLegacySetting: MMKV =
        MMKV.defaultMMKV(MMKV.SINGLE_PROCESS_MODE, AppUtils.getPackageName())

    // 当前用户 DataStore（用户隔离）
    private var curUserDataStore: DataStore<Preferences>

    // 仅用于迁移读取，按用户切换 legacy MMKV 实例
    private var curUserLegacySetting: MMKV

    // 当前UserId
    private var curUid: String = ""

    // 当前用户作用域初始化锁：用于延迟从 DataStore 同步 cur_uid，避免在 object init 阶段阻塞主线程
    private val currentUserScopeLock = Any()

    @Volatile private var hasHydratedCurrentUserScopeFromDataStore: Boolean = false

    // 用于同步 incrementTotalMessageCount 操作的锁对象
    private val messageCountLock = Any()

    private var isLoggingOut = false

    // 用于首页chat的页面请求数据的seed，每次app启动时生成固定值
    private var _randomSortSeed: Int? = null

    init {
        // 初始化阶段不执行 DataStore runBlocking，先用 legacy cur_uid 建立临时用户作用域。
        // 后续首次读取/写入用户维度数据时，再按 DataStore 真值一次性同步。
        curUid = allUserLegacySetting.decodeString(KEY_CURRENT_USER_ID) ?: ""
        curUserDataStore = createUserDataStore(curUid)
        curUserLegacySetting = createLegacyUserStore(curUid)
    }

    private fun createUserDataStore(uid: String): DataStore<Preferences> {
        return dataStore("$DATASTORE_USER_PREFIX$uid")
    }

    private fun createLegacyUserStore(uid: String): MMKV {
        return MMKV.mmkvWithID("user_$uid", MMKV.MULTI_PROCESS_MODE)
    }

    private fun migrationMarkKey(keyName: String): String {
        return "$LEGACY_MIGRATION_MARK_PREFIX$keyName"
    }

    private fun <T> readPreference(
        dataStore: DataStore<Preferences>,
        key: Preferences.Key<T>,
    ): T? {
        return runBlocking { dataStore.data.first()[key] }
    }

    private fun putStringPreference(
        dataStore: DataStore<Preferences>,
        keyName: String,
        value: String,
    ) {
        val dataKey = stringPreferencesKey(keyName)
        val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
        runBlocking {
            dataStore.edit { preferences ->
                preferences[dataKey] = value
                preferences[markKey] = true
            }
        }
    }

    private fun putBooleanPreference(
        dataStore: DataStore<Preferences>,
        keyName: String,
        value: Boolean,
    ) {
        val dataKey = booleanPreferencesKey(keyName)
        val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
        runBlocking {
            dataStore.edit { preferences ->
                preferences[dataKey] = value
                preferences[markKey] = true
            }
        }
    }

    private fun putIntPreference(
        dataStore: DataStore<Preferences>,
        keyName: String,
        value: Int,
    ) {
        val dataKey = intPreferencesKey(keyName)
        val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
        runBlocking {
            dataStore.edit { preferences ->
                preferences[dataKey] = value
                preferences[markKey] = true
            }
        }
    }

    private fun putLongPreference(
        dataStore: DataStore<Preferences>,
        keyName: String,
        value: Long,
    ) {
        val dataKey = longPreferencesKey(keyName)
        val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
        runBlocking {
            dataStore.edit { preferences ->
                preferences[dataKey] = value
                preferences[markKey] = true
            }
        }
    }

    private fun putFloatPreference(
        dataStore: DataStore<Preferences>,
        keyName: String,
        value: Float,
    ) {
        val dataKey = floatPreferencesKey(keyName)
        val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
        runBlocking {
            dataStore.edit { preferences ->
                preferences[dataKey] = value
                preferences[markKey] = true
            }
        }
    }

    private fun removePreference(
        dataStore: DataStore<Preferences>,
        keyName: String,
    ) {
        val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
        runBlocking {
            dataStore.edit { preferences ->
                val existingKey = preferences.asMap().keys.firstOrNull { key -> key.name == keyName }
                if (existingKey != null) {
                    @Suppress("UNCHECKED_CAST")
                    preferences.remove(existingKey as Preferences.Key<Any>)
                }
                preferences[markKey] = true
            }
        }
    }

    private fun isMigrationChecked(
        dataStore: DataStore<Preferences>,
        keyName: String,
    ): Boolean {
        return readPreference(dataStore, booleanPreferencesKey(migrationMarkKey(keyName))) ?: false
    }

    private fun markMigrationChecked(
        dataStore: DataStore<Preferences>,
        keyName: String,
    ) {
        val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
        runBlocking {
            dataStore.edit { preferences ->
                preferences[markKey] = true
            }
        }
    }

    private fun getStringOrNullWithMigration(
        dataStore: DataStore<Preferences>,
        keyName: String,
        legacyValueProvider: () -> String?,
    ): String? {
        val dataKey = stringPreferencesKey(keyName)
        val dataStoreValue = readPreference(dataStore, dataKey)
        if (dataStoreValue != null) {
            return dataStoreValue
        }

        if (isMigrationChecked(dataStore, keyName)) {
            return null
        }

        val legacyValue = legacyValueProvider()
        return if (legacyValue != null) {
            putStringPreference(dataStore, keyName, legacyValue)
            readPreference(dataStore, dataKey) ?: legacyValue
        } else {
            markMigrationChecked(dataStore, keyName)
            null
        }
    }

    private fun getBooleanWithMigration(
        dataStore: DataStore<Preferences>,
        legacyStore: MMKV,
        keyName: String,
        defaultValue: Boolean,
    ): Boolean {
        val dataKey = booleanPreferencesKey(keyName)
        val dataStoreValue = readPreference(dataStore, dataKey)
        if (dataStoreValue != null) {
            return dataStoreValue
        }

        if (isMigrationChecked(dataStore, keyName)) {
            return defaultValue
        }

        return if (legacyStore.containsKey(keyName)) {
            val legacyValue = legacyStore.decodeBool(keyName, defaultValue)
            putBooleanPreference(dataStore, keyName, legacyValue)
            readPreference(dataStore, dataKey) ?: legacyValue
        } else {
            markMigrationChecked(dataStore, keyName)
            defaultValue
        }
    }

    private fun getIntWithMigration(
        dataStore: DataStore<Preferences>,
        legacyStore: MMKV,
        keyName: String,
        defaultValue: Int,
    ): Int {
        val dataKey = intPreferencesKey(keyName)
        val dataStoreValue = readPreference(dataStore, dataKey)
        if (dataStoreValue != null) {
            return dataStoreValue
        }

        if (isMigrationChecked(dataStore, keyName)) {
            return defaultValue
        }

        return if (legacyStore.containsKey(keyName)) {
            val legacyValue = legacyStore.decodeInt(keyName, defaultValue)
            putIntPreference(dataStore, keyName, legacyValue)
            readPreference(dataStore, dataKey) ?: legacyValue
        } else {
            markMigrationChecked(dataStore, keyName)
            defaultValue
        }
    }

    private fun getLongWithMigration(
        dataStore: DataStore<Preferences>,
        legacyStore: MMKV,
        keyName: String,
        defaultValue: Long,
    ): Long {
        val dataKey = longPreferencesKey(keyName)
        val dataStoreValue = readPreference(dataStore, dataKey)
        if (dataStoreValue != null) {
            return dataStoreValue
        }

        if (isMigrationChecked(dataStore, keyName)) {
            return defaultValue
        }

        return if (legacyStore.containsKey(keyName)) {
            val legacyValue = legacyStore.decodeLong(keyName, defaultValue)
            putLongPreference(dataStore, keyName, legacyValue)
            readPreference(dataStore, dataKey) ?: legacyValue
        } else {
            markMigrationChecked(dataStore, keyName)
            defaultValue
        }
    }

    private fun getFloatWithMigration(
        dataStore: DataStore<Preferences>,
        legacyStore: MMKV,
        keyName: String,
        defaultValue: Float,
    ): Float {
        val dataKey = floatPreferencesKey(keyName)
        val dataStoreValue = readPreference(dataStore, dataKey)
        if (dataStoreValue != null) {
            return dataStoreValue
        }

        if (isMigrationChecked(dataStore, keyName)) {
            return defaultValue
        }

        return if (legacyStore.containsKey(keyName)) {
            val legacyValue = legacyStore.decodeFloat(keyName, defaultValue)
            putFloatPreference(dataStore, keyName, legacyValue)
            readPreference(dataStore, dataKey) ?: legacyValue
        } else {
            markMigrationChecked(dataStore, keyName)
            defaultValue
        }
    }

    private fun migratePrefixedStringKeysFromLegacy(
        dataStore: DataStore<Preferences>,
        legacyStore: MMKV,
        prefix: String,
    ) {
        val legacyKeys = legacyStore.allKeys()?.filter { key -> key.startsWith(prefix) } ?: return
        if (legacyKeys.isEmpty()) return

        runBlocking {
            dataStore.edit { preferences ->
                legacyKeys.forEach { keyName ->
                    val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
                    if (preferences[markKey] == true) return@forEach

                    val dataKey = stringPreferencesKey(keyName)
                    if (preferences[dataKey] == null) {
                        val legacyValue = legacyStore.decodeString(keyName)
                        if (legacyValue != null) {
                            preferences[dataKey] = legacyValue
                        }
                    }
                    preferences[markKey] = true
                }
            }
        }
    }

    private fun migratePrefixedBooleanKeysFromLegacy(
        dataStore: DataStore<Preferences>,
        legacyStore: MMKV,
        prefix: String,
    ) {
        val legacyKeys = legacyStore.allKeys()?.filter { key -> key.startsWith(prefix) } ?: return
        if (legacyKeys.isEmpty()) return

        runBlocking {
            dataStore.edit { preferences ->
                legacyKeys.forEach { keyName ->
                    val markKey = booleanPreferencesKey(migrationMarkKey(keyName))
                    if (preferences[markKey] == true) return@forEach

                    if (legacyStore.containsKey(keyName)) {
                        val dataKey = booleanPreferencesKey(keyName)
                        preferences[dataKey] = legacyStore.decodeBool(keyName, false)
                    }
                    preferences[markKey] = true
                }
            }
        }
    }

    private fun markLegacyKeysMigratedByPrefixes(
        dataStore: DataStore<Preferences>,
        legacyStore: MMKV,
        prefixes: Set<String>,
    ) {
        val legacyKeys =
            legacyStore.allKeys()?.filter { key -> prefixes.any { prefix -> key.startsWith(prefix) } }
                ?: return
        if (legacyKeys.isEmpty()) return

        runBlocking {
            dataStore.edit { preferences ->
                legacyKeys.forEach { keyName ->
                    preferences[booleanPreferencesKey(migrationMarkKey(keyName))] = true
                }
            }
        }
    }

    private fun removeKeysByPrefixes(
        dataStore: DataStore<Preferences>,
        prefixes: Set<String>,
    ) {
        runBlocking {
            dataStore.edit { preferences ->
                val keysToRemove =
                    preferences.asMap().keys.filter { key ->
                        prefixes.any { prefix -> key.name.startsWith(prefix) }
                    }
                keysToRemove.forEach { key ->
                    @Suppress("UNCHECKED_CAST")
                    preferences.remove(key as Preferences.Key<Any>)
                    preferences[booleanPreferencesKey(migrationMarkKey(key.name))] = true
                }
            }
        }
    }

    private fun getDataStoreKeysByPrefix(
        dataStore: DataStore<Preferences>,
        prefix: String,
    ): Set<String> {
        return runBlocking {
            dataStore.data
                .first()
                .asMap()
                .keys
                .asSequence()
                .map { key -> key.name }
                .filter { keyName -> keyName.startsWith(prefix) }
                .toSet()
        }
    }

    private fun getTrueBooleanKeySuffixesByPrefix(
        dataStore: DataStore<Preferences>,
        prefix: String,
    ): List<String> {
        return runBlocking {
            dataStore.data
                .first()
                .asMap()
                .entries
                .asSequence()
                .filter { entry -> entry.key.name.startsWith(prefix) && entry.value == true }
                .map { entry -> entry.key.name.removePrefix(prefix) }
                .distinct()
                .sorted()
                .toList()
        }
    }

    private fun getAppStringOrNull(keyName: String): String? {
        return getStringOrNullWithMigration(allUserDataStore, keyName) {
            allUserLegacySetting.decodeString(keyName)
        }
    }

    private fun getUserStringOrNull(keyName: String): String? {
        hydrateCurrentUserScopeIfNeeded()
        return getStringOrNullWithMigration(curUserDataStore, keyName) {
            curUserLegacySetting.decodeString(keyName)
        }
    }

    private fun getAppBoolean(
        keyName: String,
        defaultValue: Boolean,
    ): Boolean {
        return getBooleanWithMigration(allUserDataStore, allUserLegacySetting, keyName, defaultValue)
    }

    private fun getUserBoolean(
        keyName: String,
        defaultValue: Boolean,
    ): Boolean {
        hydrateCurrentUserScopeIfNeeded()
        return getBooleanWithMigration(curUserDataStore, curUserLegacySetting, keyName, defaultValue)
    }

    private fun getUserInt(
        keyName: String,
        defaultValue: Int,
    ): Int {
        hydrateCurrentUserScopeIfNeeded()
        return getIntWithMigration(curUserDataStore, curUserLegacySetting, keyName, defaultValue)
    }

    private fun getUserLong(
        keyName: String,
        defaultValue: Long,
    ): Long {
        hydrateCurrentUserScopeIfNeeded()
        return getLongWithMigration(curUserDataStore, curUserLegacySetting, keyName, defaultValue)
    }

    private fun getAppFloat(
        keyName: String,
        defaultValue: Float,
    ): Float {
        return getFloatWithMigration(allUserDataStore, allUserLegacySetting, keyName, defaultValue)
    }

    private fun getUserFloat(
        keyName: String,
        defaultValue: Float,
    ): Float {
        hydrateCurrentUserScopeIfNeeded()
        return getFloatWithMigration(curUserDataStore, curUserLegacySetting, keyName, defaultValue)
    }

    private fun putAppString(
        keyName: String,
        value: String,
    ) {
        putStringPreference(allUserDataStore, keyName, value)
    }

    private fun putUserString(
        keyName: String,
        value: String,
    ) {
        hydrateCurrentUserScopeIfNeeded()
        putStringPreference(curUserDataStore, keyName, value)
    }

    private fun putAppBoolean(
        keyName: String,
        value: Boolean,
    ) {
        putBooleanPreference(allUserDataStore, keyName, value)
    }

    private fun putUserBoolean(
        keyName: String,
        value: Boolean,
    ) {
        hydrateCurrentUserScopeIfNeeded()
        putBooleanPreference(curUserDataStore, keyName, value)
    }

    private fun putUserInt(
        keyName: String,
        value: Int,
    ) {
        hydrateCurrentUserScopeIfNeeded()
        putIntPreference(curUserDataStore, keyName, value)
    }

    private fun putUserLong(
        keyName: String,
        value: Long,
    ) {
        hydrateCurrentUserScopeIfNeeded()
        putLongPreference(curUserDataStore, keyName, value)
    }

    private fun putAppFloat(
        keyName: String,
        value: Float,
    ) {
        putFloatPreference(allUserDataStore, keyName, value)
    }

    private fun putUserFloat(
        keyName: String,
        value: Float,
    ) {
        hydrateCurrentUserScopeIfNeeded()
        putFloatPreference(curUserDataStore, keyName, value)
    }

    private fun removeUserKey(keyName: String) {
        hydrateCurrentUserScopeIfNeeded()
        removePreference(curUserDataStore, keyName)
    }

    private fun removeAppKey(keyName: String) {
        removePreference(allUserDataStore, keyName)
    }

    private fun updateCurrentUserScope(userId: String) {
        curUid = userId
        curUserDataStore = createUserDataStore(curUid)
        curUserLegacySetting = createLegacyUserStore(curUid)
    }

    private fun hydrateCurrentUserScopeIfNeeded() {
        if (hasHydratedCurrentUserScopeFromDataStore) return

        synchronized(currentUserScopeLock) {
            if (hasHydratedCurrentUserScopeFromDataStore) return
            val userId = getAppStringOrNull(KEY_CURRENT_USER_ID) ?: ""
            if (userId != curUid) {
                updateCurrentUserScope(userId)
            }
            hasHydratedCurrentUserScopeFromDataStore = true
        }
    }

    fun getCurUserID(): String {
        hydrateCurrentUserScopeIfNeeded()
        return curUid
    }

    /** 切换用户 对应Guest登录Google账户 Google账户退出登录，到Guest账户 */
    fun changeUser(uid: String) {
        // 与 hydrateCurrentUserScopeIfNeeded 使用同一把锁，避免并发下用户作用域被旧值回滚。
        synchronized(currentUserScopeLock) {
            updateCurrentUserScope(uid)
            hasHydratedCurrentUserScopeFromDataStore = true
        }
        putAppString(KEY_CURRENT_USER_ID, uid)
    }

    fun setToken(token: String) {
        putUserString(KEY_TOKEN, token)
    }

    fun getCurToken(): String {
        return getUserStringOrNull(KEY_TOKEN) ?: ""
    }

    fun isLogin(): Boolean {
        return getCurUserID().isNotEmpty() && getCurToken().isNotEmpty()
    }

    /** 登录接口后，本地处理登录业务的数据逻辑 */
    fun login(uid: String, token: String) {
        // 先清除客户端缓存，确保旧客户端不会残留
        // 这样可以避免token更新和客户端获取之间的竞态条件
        IntyNetworkManager.clearClientCache()
        NetServiceMgr.clearCache()

        // 然后更新token
        changeUser(uid)
        setToken(token)

        // 再次清除缓存，确保使用新token创建客户端
        // 虽然getClient()会清除旧token的缓存，但这里双重保险
        IntyNetworkManager.clearClientCache()
        NetServiceMgr.clearCache()
    }

    fun setKeyboardHeight(height: Float) {
        putAppFloat(KEY_KEYBOARD_HEIGHT, height)
    }

    fun getKeyboardHeight(): Float {
        return getAppFloat(KEY_KEYBOARD_HEIGHT, 0f)
    }

    /** 记录是否显示keepTalking按钮（全局设置） */
    fun setShowKeepTalking(show: Boolean) {
        putUserBoolean("show_keep_talking", show)
    }

    fun isShowKeepTalking(): Boolean {
        return getUserBoolean("show_keep_talking", false)
    }

    /** 检查用户是否手动设置过 Keep Talking（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetKeepTalking(): Boolean {
        return getUserBoolean("user_set_keep_talking", false)
    }

    /** 标记用户已手动设置过 Keep Talking */
    fun markUserSetKeepTalking() {
        putUserBoolean("user_set_keep_talking", true)
    }

    /** 自动播放语音消息（全局设置，默认开启） */
    fun setAutoPlayAudio(play: Boolean) {
        putUserBoolean("auto_play_audio", play)
    }

    fun isAutoPlayAudio(): Boolean {
        // 默认值为true（开启）
        return getUserBoolean("auto_play_audio", true)
    }

    /** 检查用户是否手动设置过 Auto Play Voice（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetAutoPlayVoice(): Boolean {
        return getUserBoolean("user_set_auto_play_voice", false)
    }

    /** 标记用户已手动设置过 Auto Play Voice */
    fun markUserSetAutoPlayVoice() {
        putUserBoolean("user_set_auto_play_voice", true)
    }

    /** 自动播放背景动画（全局设置，默认开启） */
    fun setAutoPlayAnimation(enabled: Boolean) {
        putUserBoolean("auto_play_animation", enabled)
    }

    /** 流式显示聊天消息 */
    fun setTextStreaming(enabled: Boolean) {
        putUserBoolean("text_streaming", enabled)
    }

    fun isAutoPlayAnimation(): Boolean {
        return getUserBoolean("auto_play_animation", true)
    }

    /** 是否流式显示聊天消息 */
    fun isTextStreaming(): Boolean {
        return getUserBoolean("text_streaming", true)
    }

    /** Vibe Mode 开关状态（仅限订阅用户） */
    fun setVibeModeEnabled(enabled: Boolean) {
        putUserBoolean("vibe_mode_enabled", enabled)
    }

    fun isVibeModeEnabled(): Boolean {
        return getUserBoolean("vibe_mode_enabled", false)
    }

    /** 禁用 IntelliMate tips 弹窗（用户偏好设置） */
    fun setTipsDisabled(disabled: Boolean) {
        putUserBoolean("tips_disabled", disabled)
    }

    fun isTipsDisabled(): Boolean {
        return getUserBoolean("tips_disabled", false)
    }

    /** 获取 IntelliMate tips 弹窗的上次展示时间（毫秒时间戳）。 */
    fun getIntelliMateTipLastShowTimeMillis(): Long {
        // 默认值为很小的值，确保首次检查一定可以展示。
        return getUserLong(KEY_INTELLIMATE_TIP_LAST_SHOW_TIME, -1L)
    }

    /** 设置 IntelliMate tips 弹窗的上次展示时间（毫秒时间戳）。 */
    fun setIntelliMateTipLastShowTimeMillis(timestampMillis: Long) {
        putUserLong(KEY_INTELLIMATE_TIP_LAST_SHOW_TIME, timestampMillis)
    }

    /**
     * 判断此刻是否允许展示 IntelliMate tips 弹窗。
     *
     * 规则：最多每 8 小时展示一次（同一用户维度）。
     */
    fun canShowIntelliMateTipNow(nowMillis: Long = System.currentTimeMillis()): Boolean {
        val lastShownMillis = getIntelliMateTipLastShowTimeMillis()
        if (lastShownMillis < 0L) return true
        return nowMillis - lastShownMillis >= INTELLIMATE_TIP_MIN_INTERVAL_MILLIS
    }

    /** 检查用户是否手动设置过 Auto Play Animation */
    fun hasUserSetAutoPlayAnimation(): Boolean {
        return getUserBoolean("user_set_auto_play_animation", false)
    }

    /** 标记用户已手动设置过 Auto Play Animation */
    fun markUserSetAutoPlayAnimation() {
        putUserBoolean("user_set_auto_play_animation", true)
    }

    /** 标记用户已手动设置过 Text Streaming */
    fun markUserTextStreaming() {
        putUserBoolean("user_set_text_streaming", true)
    }

    /** 显示场景动作输入按钮（全局设置，默认关闭） */
    fun setShowSceneActionButton(show: Boolean) {
        putUserBoolean("show_scene_action_button", show)
    }

    fun isShowSceneActionButton(): Boolean {
        // 默认值为false（关闭）
        return getUserBoolean("show_scene_action_button", false)
    }

    /** 检查用户是否手动设置过 Show Scene Action Button（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetSceneActionButton(): Boolean {
        return getUserBoolean("user_set_scene_action_button", false)
    }

    /** 标记用户已手动设置过 Show Scene Action Button */
    fun markUserSetSceneActionButton() {
        putUserBoolean("user_set_scene_action_button", true)
    }

    /** 消息列表是否全屏（全局设置，默认关闭） */
    fun setChatListFullScreen(fullScreen: Boolean) {
        putUserBoolean("chat_list_full_screen", fullScreen)
    }

    fun isChatListFullScreen(): Boolean {
        // 默认值为 false（关闭全屏），避免消息列表遮挡角色脸部
        return getUserBoolean("chat_list_full_screen", false)
    }

    /** 聊天消息字体大小（单位 sp，默认 14f） */
    fun setChatFontSizeSp(size: Float) {
        putUserFloat(KEY_CHAT_FONT_SIZE_SP, size)
    }

    fun getChatFontSizeSp(): Float {
        return getUserFloat(KEY_CHAT_FONT_SIZE_SP, DEFAULT_CHAT_FONT_SIZE_SP)
    }

    /** 聊天模型选择（全局设置，默认 Gemini 3 Flash） */
    fun setChatModelId(modelId: String) {
        putUserString(KEY_CHAT_MODEL_ID, modelId)
    }

    fun getChatModelId(): String {
        return getUserStringOrNull(KEY_CHAT_MODEL_ID) ?: DEFAULT_CHAT_MODEL_ID
    }

    fun getLastResubReminderDialogShowTime(): Long {
        return getUserLong(KEY_RESUB_REMINDER_LAST_TIME, 0L)
    }

    fun setLastResubReminderDialogShowTime(timestampSeconds: Long) {
        putUserLong(KEY_RESUB_REMINDER_LAST_TIME, timestampSeconds)
    }

    fun getResubReminderDialogShowCount(): Int {
        return getUserInt(KEY_RESUB_REMINDER_SHOW_COUNT, 0)
    }

    fun setResubReminderDialogShowCount(count: Int) {
        putUserInt(KEY_RESUB_REMINDER_SHOW_COUNT, count)
    }

    fun getFeedbackDialogLastShowTime(): Long {
        // 默认值为很大的负值，保证第一次检查一定超出显示时长阈值。
        return getUserLong(KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME, -1L)
    }

    fun setFeedbackDialogLastShowTime(timestampMillis: Long) {
        putUserLong(KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME, timestampMillis)
    }

    /** 获取总消息数（跨所有AI角色） */
    fun getTotalMessageCount(): Int {
        return getUserInt(KEY_TOTAL_MESSAGE_COUNT, 0)
    }

    /**
     * 增加总消息数并返回新的计数
     *
     * 使用同步锁确保读-改-写操作的原子性，防止并发调用时丢失增量。 这对于反馈对话框触发逻辑至关重要，因为它依赖于消息计数达到100的倍数。
     */
    fun incrementTotalMessageCount(): Int {
        synchronized(messageCountLock) {
            val currentCount = getTotalMessageCount()
            val newCount = currentCount + 1
            putUserInt(KEY_TOTAL_MESSAGE_COUNT, newCount)
            return newCount
        }
    }

    /** 记录消息Tab是否需要显示推送红点 */
    fun setMessagesTabHasPush(hasPush: Boolean) {
        putUserBoolean(KEY_MESSAGES_TAB_HAS_PUSH, hasPush)
    }

    fun hasMessagesTabPush(): Boolean {
        return getUserBoolean(KEY_MESSAGES_TAB_HAS_PUSH, false)
    }

    /** 记录特定会话是否有推送未读 */
    fun setConversationHasPush(agentId: String, hasPush: Boolean) {
        val key = "$KEY_CONVERSATION_PUSH_PREFIX$agentId"
        if (hasPush) {
            putUserBoolean(key, true)
        } else {
            removeUserKey(key)
        }
    }

    fun hasConversationPush(agentId: String): Boolean {
        return getUserBoolean("$KEY_CONVERSATION_PUSH_PREFIX$agentId", false)
    }

    // 标记是否已经有可用的App更新，用于红点标记
    fun hasAppUpdateTips(): Boolean {
        return getUserBoolean(KEY_APP_UPDATE_TIPS, false)
    }

    fun setAppUpdateTips(showed: Boolean) {
        putUserBoolean(KEY_APP_UPDATE_TIPS, showed)
    }

    fun logout() {
        isLoggingOut = true
        setToken("")
        // 延迟重置标志，确保401处理器有时间识别
        Handler(Looper.getMainLooper()).postDelayed({ isLoggingOut = false }, 2000)
    }

    fun isLoggingOut(): Boolean {
        return isLoggingOut
    }

    // 用于推荐接口后端sort随机排序的seed种子
    fun sortSeed(): Int {
        return getUserInt(KEY_SORT_SEED, 0)
    }

    // 用于首页chat的页面请求数据的seed，每次app启动时生成固定值
    fun randomSortSeed(): Int {
        if (_randomSortSeed == null) {
            _randomSortSeed = Random.Default.nextInt()
        }
        return _randomSortSeed!!
    }

    fun updateSortSeed(seed: Int) {
        putUserInt(KEY_SORT_SEED, seed)
    }

    // region 通用的用户信息存储方法（不依赖具体的 UserProfile 类）
    fun setUserProfileData(key: String, value: String) {
        putUserString("$KEY_USER_PROFILE_PREFIX$key", value)
    }

    fun getUserProfileData(key: String): String? {
        return getUserStringOrNull("$KEY_USER_PROFILE_PREFIX$key")
    }

    fun setUserProfileBoolean(key: String, value: Boolean) {
        putUserBoolean("$KEY_USER_PROFILE_PREFIX$key", value)
    }

    fun getUserProfileBoolean(key: String, defaultValue: Boolean = false): Boolean {
        return getUserBoolean("$KEY_USER_PROFILE_PREFIX$key", defaultValue)
    }

    fun setUserProfileInt(key: String, value: Int) {
        putUserInt("$KEY_USER_PROFILE_PREFIX$key", value)
    }

    fun getUserProfileInt(key: String, defaultValue: Int = 0): Int {
        return getUserInt("$KEY_USER_PROFILE_PREFIX$key", defaultValue)
    }

    fun hasUserProfileData(key: String): Boolean {
        return getUserProfileData(key)?.isNotEmpty() == true
    }

    fun clearUserProfileData(key: String) {
        removeUserKey("$KEY_USER_PROFILE_PREFIX$key")
    }

    fun clearAllUserProfileData() {
        removeKeysByPrefixes(curUserDataStore, setOf(KEY_USER_PROFILE_PREFIX))
        markLegacyKeysMigratedByPrefixes(
            curUserDataStore,
            curUserLegacySetting,
            setOf(KEY_USER_PROFILE_PREFIX),
        )
    }

    fun hasShowGuest(): Boolean {
        return getAppBoolean(KEY_SHOW_GUEST, false)
    }

    fun setShowGuested() {
        putAppBoolean(KEY_SHOW_GUEST, true)
    }

    // region 应用级别的通用存储方法（不依赖用户）
    /** 设置应用级别的数据（所有用户共享） */
    fun setAppData(key: String, value: String) {
        putAppString("$KEY_APP_DATA_PREFIX$key", value)
    }

    /** 获取应用级别的数据 */
    fun getAppData(key: String): String? {
        return getAppStringOrNull("$KEY_APP_DATA_PREFIX$key")
    }

    /** 检查应用级别的数据是否存在 */
    fun hasAppData(key: String): Boolean {
        return getAppData(key)?.isNotEmpty() == true
    }

    /** 清除应用级别的数据 */
    fun clearAppData(key: String) {
        removeAppKey("$KEY_APP_DATA_PREFIX$key")
    }

    /** 获取所有应用级别的数据键（用于批量操作） */
    fun getAllAppDataKeys(): Set<String> {
        migratePrefixedStringKeysFromLegacy(
            allUserDataStore,
            allUserLegacySetting,
            KEY_APP_DATA_PREFIX,
        )
        return getDataStoreKeysByPrefix(allUserDataStore, KEY_APP_DATA_PREFIX)
    }

    // endregion

    // endregion

    // region 聊天数据持久化相关方法

    /** 清除指定agent的聊天数据（清理可能存在的旧数据） */
    fun clearChatData(agentId: String) {
        removeUserKey("$KEY_CHAT_MESSAGES_PREFIX$agentId")
        removeUserKey("$KEY_CHAT_OFFSET_PREFIX$agentId")
        removeUserKey("$KEY_CHAT_HAS_MORE_PREFIX$agentId")
        removeUserKey("$KEY_CHAT_INITIAL_LOADED_PREFIX$agentId")
    }

    /** 清除所有聊天数据 */
    fun clearAllChatData() {
        val chatPrefixes =
            setOf(
                KEY_CHAT_MESSAGES_PREFIX,
                KEY_CHAT_OFFSET_PREFIX,
                KEY_CHAT_HAS_MORE_PREFIX,
                KEY_CHAT_INITIAL_LOADED_PREFIX,
            )
        removeKeysByPrefixes(curUserDataStore, chatPrefixes)
        markLegacyKeysMigratedByPrefixes(curUserDataStore, curUserLegacySetting, chatPrefixes)
    }

    // endregion

    // region Explore收藏状态

    /** 设置 Explore 页面角色卡的收藏状态 */
    fun setExploreAgentFavorite(agentId: String, favorite: Boolean) {
        if (agentId.isBlank()) return
        val key = "$KEY_PREFIX_EXPLORE_FAVORITE$agentId"
        if (favorite) {
            putUserBoolean(key, true)
        } else {
            removeUserKey(key)
        }
    }

    /** 获取 Explore 页面角色卡的收藏状态 */
    fun isExploreAgentFavorite(agentId: String): Boolean {
        if (agentId.isBlank()) return false
        return getUserBoolean("$KEY_PREFIX_EXPLORE_FAVORITE$agentId", false)
    }

    /** 获取所有已收藏的 Explore 角色ID */
    fun getExploreFavoriteAgentIds(): List<String> {
        migratePrefixedBooleanKeysFromLegacy(
            curUserDataStore,
            curUserLegacySetting,
            KEY_PREFIX_EXPLORE_FAVORITE,
        )
        return getTrueBooleanKeySuffixesByPrefix(curUserDataStore, KEY_PREFIX_EXPLORE_FAVORITE)
    }

    // endregion

    // region 聊天背景图片相关设置

    /** 设置指定agent的自定义聊天背景图片 */
    fun setChatBackgroundImage(agentId: String, imageUrl: String) {
        setUserProfileData("chat_background_$agentId", imageUrl)
    }

    /** 获取指定agent的自定义聊天背景图片 */
    fun getChatBackgroundImage(agentId: String): String? {
        return getUserProfileData("chat_background_$agentId")?.takeIf { it.isNotBlank() }
    }

    /** 清除指定agent的自定义聊天背景图片（恢复为默认） */
    fun clearChatBackgroundImage(agentId: String) {
        clearUserProfileData("chat_background_$agentId")
    }

    /** 检查指定agent是否有自定义聊天背景图片 */
    fun hasCustomChatBackground(agentId: String): Boolean {
        return hasUserProfileData("chat_background_$agentId")
    }

    // endregion

    // region 会话Pin/Hide相关设置

    /** 设置会话置顶状态 */
    fun setConversationPinned(agentId: String, pinned: Boolean) {
        putUserBoolean("$KEY_CONVERSATION_PINNED_PREFIX$agentId", pinned)
    }

    /** 获取会话置顶状态 */
    fun isConversationPinned(agentId: String): Boolean {
        return getUserBoolean("$KEY_CONVERSATION_PINNED_PREFIX$agentId", false)
    }

    /** 设置会话隐藏状态 */
    fun setConversationHidden(agentId: String, hidden: Boolean) {
        putUserBoolean("$KEY_CONVERSATION_HIDDEN_PREFIX$agentId", hidden)
        if (hidden) {
            // 记录隐藏时的时间戳，用于判断是否有新消息
            putUserLong("$KEY_CONVERSATION_HIDDEN_TIME_PREFIX$agentId", System.currentTimeMillis())
        } else {
            removeUserKey("$KEY_CONVERSATION_HIDDEN_TIME_PREFIX$agentId")
        }
    }

    /** 获取会话隐藏状态 */
    fun isConversationHidden(agentId: String): Boolean {
        return getUserBoolean("$KEY_CONVERSATION_HIDDEN_PREFIX$agentId", false)
    }

    /** 获取会话隐藏时间（用于判断是否应该恢复显示） */
    fun getConversationHiddenTime(agentId: String): Long {
        return getUserLong("$KEY_CONVERSATION_HIDDEN_TIME_PREFIX$agentId", 0L)
    }

    /** 检查会话是否有新消息（用于自动取消隐藏） */
    fun hasNewMessageSinceHidden(agentId: String, lastMessageTime: String): Boolean {
        val hiddenTime = getConversationHiddenTime(agentId)
        if (hiddenTime == 0L) return false

        // 将 lastMessageTime（ISO 8601 格式）转换为时间戳进行比较
        val messageTimeStamp =
            ai.sxwl.android.utils.TimeUtils.parseIsoTimeToTimestamp(lastMessageTime)
        return if (messageTimeStamp != null) {
            messageTimeStamp > hiddenTime
        } else {
            false
        }
    }

    // endregion

}
