package ai.sxwl.android.data.store

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.http.IntyNetworkManager
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
import kotlin.random.Random
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

private const val KEY_CUR_UID = "cur_uid"
private const val ALL_USER_SETTINGS_STORE_NAME = "inty_all_user_setting"
private const val USER_SETTINGS_STORE_PREFIX = "inty_user_"
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

// IntelliMate Tips 展示频率：最多每 8 小时一次（降低打扰）
private const val INTELLIMATE_TIP_MIN_INTERVAL_MILLIS = 8 * 60 * 60 * 1000L

object IntySetting {

    // 当前UserId
    private var curUid: String = ""

    // 用于同步 incrementTotalMessageCount 操作的锁对象
    private val messageCountLock = Any()

    init {
        curUid = getStringValue(allUserStore(), KEY_CUR_UID) ?: ""
    }

    fun getCurUserID(): String {
        return curUid
    }

    /** 切换用户 对应Guest登录Google账户 Google账户退出登录，到Guest账户 */
    fun changeUser(uid: String) {
        curUid = uid
        putStringValue(allUserStore(), KEY_CUR_UID, uid)
    }

    fun setToken(token: String) {
        putStringValue(curUserStore(), "token", token)
    }

    fun getCurToken(): String {
        return getStringValue(curUserStore(), "token") ?: ""
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
        putFloatValue(allUserStore(), "keyboardHeight", height)
    }

    fun getKeyboardHeight(): Float {
        return getFloatValue(allUserStore(), "keyboardHeight", 0f)
    }

    /** 记录是否显示keepTalking按钮（全局设置） */
    fun setShowKeepTalking(show: Boolean) {
        putBooleanValue(curUserStore(), "show_keep_talking", show)
    }

    fun isShowKeepTalking(): Boolean {
        return getBooleanValue(curUserStore(), "show_keep_talking", false)
    }

    /** 检查用户是否手动设置过 Keep Talking（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetKeepTalking(): Boolean {
        return getBooleanValue(curUserStore(), "user_set_keep_talking", false)
    }

    /** 标记用户已手动设置过 Keep Talking */
    fun markUserSetKeepTalking() {
        putBooleanValue(curUserStore(), "user_set_keep_talking", true)
    }

    /** 自动播放语音消息（全局设置，默认开启） */
    fun setAutoPlayAudio(play: Boolean) {
        putBooleanValue(curUserStore(), "auto_play_audio", play)
    }

    fun isAutoPlayAudio(): Boolean {
        // 默认值为true（开启）
        return getBooleanValue(curUserStore(), "auto_play_audio", true)
    }

    /** 检查用户是否手动设置过 Auto Play Voice（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetAutoPlayVoice(): Boolean {
        return getBooleanValue(curUserStore(), "user_set_auto_play_voice", false)
    }

    /** 标记用户已手动设置过 Auto Play Voice */
    fun markUserSetAutoPlayVoice() {
        putBooleanValue(curUserStore(), "user_set_auto_play_voice", true)
    }

    /** 自动播放背景动画（全局设置，默认开启） */
    fun setAutoPlayAnimation(enabled: Boolean) {
        putBooleanValue(curUserStore(), "auto_play_animation", enabled)
    }

    /** 流式显示聊天消息 */
    fun setTextStreaming(enabled: Boolean) {
        putBooleanValue(curUserStore(), "text_streaming", enabled)
    }

    fun isAutoPlayAnimation(): Boolean {
        return getBooleanValue(curUserStore(), "auto_play_animation", true)
    }

    /** 是否流式显示聊天消息 */
    fun isTextStreaming(): Boolean {
        return getBooleanValue(curUserStore(), "text_streaming", true)
    }

    /** Vibe Mode 开关状态（仅限订阅用户） */
    fun setVibeModeEnabled(enabled: Boolean) {
        putBooleanValue(curUserStore(), "vibe_mode_enabled", enabled)
    }

    fun isVibeModeEnabled(): Boolean {
        return getBooleanValue(curUserStore(), "vibe_mode_enabled", false)
    }

    /** 禁用 IntelliMate tips 弹窗（用户偏好设置） */
    fun setTipsDisabled(disabled: Boolean) {
        putBooleanValue(curUserStore(), "tips_disabled", disabled)
    }

    fun isTipsDisabled(): Boolean {
        return getBooleanValue(curUserStore(), "tips_disabled", false)
    }

    /** 获取 IntelliMate tips 弹窗的上次展示时间（毫秒时间戳）。 */
    fun getIntelliMateTipLastShowTimeMillis(): Long {
        // 默认值为很小的值，确保首次检查一定可以展示。
        return getLongValue(curUserStore(), KEY_INTELLIMATE_TIP_LAST_SHOW_TIME, -1L)
    }

    /** 设置 IntelliMate tips 弹窗的上次展示时间（毫秒时间戳）。 */
    fun setIntelliMateTipLastShowTimeMillis(timestampMillis: Long) {
        putLongValue(curUserStore(), KEY_INTELLIMATE_TIP_LAST_SHOW_TIME, timestampMillis)
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
        return getBooleanValue(curUserStore(), "user_set_auto_play_animation", false)
    }

    /** 标记用户已手动设置过 Auto Play Animation */
    fun markUserSetAutoPlayAnimation() {
        putBooleanValue(curUserStore(), "user_set_auto_play_animation", true)
    }

    /** 标记用户已手动设置过 Text Streaming */
    fun markUserTextStreaming() {
        putBooleanValue(curUserStore(), "user_set_text_streaming", true)
    }

    /** 显示场景动作输入按钮（全局设置，默认关闭） */
    fun setShowSceneActionButton(show: Boolean) {
        putBooleanValue(curUserStore(), "show_scene_action_button", show)
    }

    fun isShowSceneActionButton(): Boolean {
        // 默认值为false（关闭）
        return getBooleanValue(curUserStore(), "show_scene_action_button", false)
    }

    /** 检查用户是否手动设置过 Show Scene Action Button（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetSceneActionButton(): Boolean {
        return getBooleanValue(curUserStore(), "user_set_scene_action_button", false)
    }

    /** 标记用户已手动设置过 Show Scene Action Button */
    fun markUserSetSceneActionButton() {
        putBooleanValue(curUserStore(), "user_set_scene_action_button", true)
    }

    /** 消息列表是否全屏（全局设置，默认关闭） */
    fun setChatListFullScreen(fullScreen: Boolean) {
        putBooleanValue(curUserStore(), "chat_list_full_screen", fullScreen)
    }

    fun isChatListFullScreen(): Boolean {
        // 默认值为 false（关闭全屏），避免消息列表遮挡角色脸部
        return getBooleanValue(curUserStore(), "chat_list_full_screen", false)
    }

    /** 聊天消息字体大小（单位 sp，默认 14f） */
    fun setChatFontSizeSp(size: Float) {
        putFloatValue(curUserStore(), KEY_CHAT_FONT_SIZE_SP, size)
    }

    fun getChatFontSizeSp(): Float {
        return getFloatValue(curUserStore(), KEY_CHAT_FONT_SIZE_SP, DEFAULT_CHAT_FONT_SIZE_SP)
    }

    /** 聊天模型选择（全局设置，默认 Gemini 3 Flash） */
    fun setChatModelId(modelId: String) {
        putStringValue(curUserStore(), KEY_CHAT_MODEL_ID, modelId)
    }

    fun getChatModelId(): String {
        return getStringValue(curUserStore(), KEY_CHAT_MODEL_ID, DEFAULT_CHAT_MODEL_ID)
            ?: DEFAULT_CHAT_MODEL_ID
    }

    fun getLastResubReminderDialogShowTime(): Long {
        return getLongValue(curUserStore(), KEY_RESUB_REMINDER_LAST_TIME, 0L)
    }

    fun setLastResubReminderDialogShowTime(timestampSeconds: Long) {
        putLongValue(curUserStore(), KEY_RESUB_REMINDER_LAST_TIME, timestampSeconds)
    }

    fun getResubReminderDialogShowCount(): Int {
        return getIntValue(curUserStore(), KEY_RESUB_REMINDER_SHOW_COUNT, 0)
    }

    fun setResubReminderDialogShowCount(count: Int) {
        putIntValue(curUserStore(), KEY_RESUB_REMINDER_SHOW_COUNT, count)
    }

    fun getFeedbackDialogLastShowTime(): Long {
        // 默认值为很大的负值，保证第一次检查一定超出显示时长阈值。
        return getLongValue(curUserStore(), KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME, -1L)
    }

    fun setFeedbackDialogLastShowTime(timestampMillis: Long) {
        putLongValue(curUserStore(), KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME, timestampMillis)
    }

    /** 获取总消息数（跨所有AI角色） */
    fun getTotalMessageCount(): Int {
        return getIntValue(curUserStore(), KEY_TOTAL_MESSAGE_COUNT, 0)
    }

    /**
     * 增加总消息数并返回新的计数
     *
     * 使用同步锁确保读-改-写操作的原子性，防止并发调用时丢失增量。 这对于反馈对话框触发逻辑至关重要，因为它依赖于消息计数达到100的倍数。
     */
    fun incrementTotalMessageCount(): Int {
        synchronized(messageCountLock) {
            var newCount = 0
            runBlocking {
                val totalMessageCountKey = intPreferencesKey(KEY_TOTAL_MESSAGE_COUNT)
                curUserStore().edit { preferences ->
                    val currentCount = preferences[totalMessageCountKey] ?: 0
                    newCount = currentCount + 1
                    preferences[totalMessageCountKey] = newCount
                }
            }
            return newCount
        }
    }

    /** 记录消息Tab是否需要显示推送红点 */
    fun setMessagesTabHasPush(hasPush: Boolean) {
        putBooleanValue(curUserStore(), KEY_MESSAGES_TAB_HAS_PUSH, hasPush)
    }

    fun hasMessagesTabPush(): Boolean {
        return getBooleanValue(curUserStore(), KEY_MESSAGES_TAB_HAS_PUSH, false)
    }

    /** 记录特定会话是否有推送未读 */
    fun setConversationHasPush(agentId: String, hasPush: Boolean) {
        val key = "$KEY_CONVERSATION_PUSH_PREFIX$agentId"
        if (hasPush) {
            putBooleanValue(curUserStore(), key, true)
        } else {
            removeKeyValue(curUserStore(), key)
        }
    }

    fun hasConversationPush(agentId: String): Boolean {
        return getBooleanValue(curUserStore(), "$KEY_CONVERSATION_PUSH_PREFIX$agentId", false)
    }

    // 标记是否已经有可用的App更新，用于红点标记
    fun hasAppUpdateTips(): Boolean {
        return getBooleanValue(curUserStore(), "has_app_update_tips", false)
    }

    fun setAppUpdateTips(showed: Boolean) {
        putBooleanValue(curUserStore(), "has_app_update_tips", showed)
    }

    private var isLoggingOut = false

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
        return getIntValue(curUserStore(), "current_sort_seed", 0)
    }

    // 用于首页chat的页面请求数据的seed，每次app启动时生成固定值
    private var _randomSortSeed: Int? = null

    fun randomSortSeed(): Int {
        if (_randomSortSeed == null) {
            _randomSortSeed = Random.Default.nextInt()
        }
        return _randomSortSeed!!
    }

    fun updateSortSeed(seed: Int) {
        putIntValue(curUserStore(), "current_sort_seed", seed)
    }

    // region 通用的用户信息存储方法（不依赖具体的 UserProfile 类）
    fun setUserProfileData(key: String, value: String) {
        putStringValue(curUserStore(), "user_profile_$key", value)
    }

    fun getUserProfileData(key: String): String? {
        return getStringValue(curUserStore(), "user_profile_$key")
    }

    fun setUserProfileBoolean(key: String, value: Boolean) {
        putBooleanValue(curUserStore(), "user_profile_$key", value)
    }

    fun getUserProfileBoolean(key: String, defaultValue: Boolean = false): Boolean {
        return getBooleanValue(curUserStore(), "user_profile_$key", defaultValue)
    }

    fun setUserProfileInt(key: String, value: Int) {
        putIntValue(curUserStore(), "user_profile_$key", value)
    }

    fun getUserProfileInt(key: String, defaultValue: Int = 0): Int {
        return getIntValue(curUserStore(), "user_profile_$key", defaultValue)
    }

    fun hasUserProfileData(key: String): Boolean {
        return getStringValue(curUserStore(), "user_profile_$key")?.isNotEmpty() == true
    }

    fun clearUserProfileData(key: String) {
        removeKeyValue(curUserStore(), "user_profile_$key")
    }

    fun clearAllUserProfileData() {
        removeKeysByPrefix(curUserStore(), setOf("user_profile_"))
    }

    fun hasShowGuest(): Boolean {
        return getBooleanValue(allUserStore(), "show_guest", false)
    }

    fun setShowGuested() {
        putBooleanValue(allUserStore(), "show_guest", true)
    }

    // region 应用级别的通用存储方法（不依赖用户）
    /** 设置应用级别的数据（所有用户共享） */
    fun setAppData(key: String, value: String) {
        putStringValue(allUserStore(), "app_data_$key", value)
    }

    /** 获取应用级别的数据 */
    fun getAppData(key: String): String? {
        return getStringValue(allUserStore(), "app_data_$key")
    }

    /** 检查应用级别的数据是否存在 */
    fun hasAppData(key: String): Boolean {
        return getStringValue(allUserStore(), "app_data_$key")?.isNotEmpty() == true
    }

    /** 清除应用级别的数据 */
    fun clearAppData(key: String) {
        removeKeyValue(allUserStore(), "app_data_$key")
    }

    /** 获取所有应用级别的数据键（用于批量操作） */
    fun getAllAppDataKeys(): Set<String> {
        return getAllKeyNames(allUserStore()).filter { it.startsWith("app_data_") }.toSet()
    }

    // endregion

    // endregion

    // region 聊天数据持久化相关方法

    /** 清除指定agent的聊天数据（清理可能存在的旧数据） */
    fun clearChatData(agentId: String) {
        removeKeyValue(curUserStore(), "chat_messages_$agentId")
        removeKeyValue(curUserStore(), "chat_offset_$agentId")
        removeKeyValue(curUserStore(), "chat_has_more_$agentId")
        removeKeyValue(curUserStore(), "chat_initial_loaded_$agentId")
    }

    /** 清除所有聊天数据 */
    fun clearAllChatData() {
        removeKeysByPrefix(
            curUserStore(),
            setOf("chat_messages_", "chat_offset_", "chat_has_more_", "chat_initial_loaded_"),
        )
    }

    // endregion

    // region Explore收藏状态

    /** 设置 Explore 页面角色卡的收藏状态 */
    fun setExploreAgentFavorite(agentId: String, favorite: Boolean) {
        if (agentId.isBlank()) return
        val key = "$KEY_PREFIX_EXPLORE_FAVORITE$agentId"
        if (favorite) {
            putBooleanValue(curUserStore(), key, true)
        } else {
            removeKeyValue(curUserStore(), key)
        }
    }

    /** 获取 Explore 页面角色卡的收藏状态 */
    fun isExploreAgentFavorite(agentId: String): Boolean {
        if (agentId.isBlank()) return false
        return getBooleanValue(curUserStore(), "$KEY_PREFIX_EXPLORE_FAVORITE$agentId", false)
    }

    /** 获取所有已收藏的 Explore 角色ID */
    fun getExploreFavoriteAgentIds(): List<String> {
        val preferences = readPreferences(curUserStore())
        return preferences
            .asMap()
            .asSequence()
            .map { it.key.name to it.value }
            .filter { it.first.startsWith(KEY_PREFIX_EXPLORE_FAVORITE) }
            .mapNotNull { (key, value) ->
                val agentId = key.removePrefix(KEY_PREFIX_EXPLORE_FAVORITE)
                if (value == true) agentId else null
            }
            .distinct()
            .sorted()
            .toList()
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
        putBooleanValue(curUserStore(), "conversation_pinned_$agentId", pinned)
    }

    /** 获取会话置顶状态 */
    fun isConversationPinned(agentId: String): Boolean {
        return getBooleanValue(curUserStore(), "conversation_pinned_$agentId", false)
    }

    /** 设置会话隐藏状态 */
    fun setConversationHidden(agentId: String, hidden: Boolean) {
        putBooleanValue(curUserStore(), "conversation_hidden_$agentId", hidden)
        if (hidden) {
            // 记录隐藏时的时间戳，用于判断是否有新消息
            putLongValue(curUserStore(), "conversation_hidden_time_$agentId", System.currentTimeMillis())
        } else {
            removeKeyValue(curUserStore(), "conversation_hidden_time_$agentId")
        }
    }

    /** 获取会话隐藏状态 */
    fun isConversationHidden(agentId: String): Boolean {
        return getBooleanValue(curUserStore(), "conversation_hidden_$agentId", false)
    }

    /** 获取会话隐藏时间（用于判断是否应该恢复显示） */
    fun getConversationHiddenTime(agentId: String): Long {
        return getLongValue(curUserStore(), "conversation_hidden_time_$agentId", 0L)
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

    private fun allUserStore(): DataStore<Preferences> = dataStore(ALL_USER_SETTINGS_STORE_NAME)

    private fun curUserStore(): DataStore<Preferences> = dataStore("$USER_SETTINGS_STORE_PREFIX$curUid")

    private fun getStringValue(
        store: DataStore<Preferences>,
        key: String,
        defaultValue: String? = null,
    ): String? {
        val preferenceKey = stringPreferencesKey(key)
        return runBlocking { store.data.first()[preferenceKey] ?: defaultValue }
    }

    private fun putStringValue(store: DataStore<Preferences>, key: String, value: String) {
        val preferenceKey = stringPreferencesKey(key)
        runBlocking { store.edit { preferences -> preferences[preferenceKey] = value } }
    }

    private fun getBooleanValue(
        store: DataStore<Preferences>,
        key: String,
        defaultValue: Boolean,
    ): Boolean {
        val preferenceKey = booleanPreferencesKey(key)
        return runBlocking { store.data.first()[preferenceKey] ?: defaultValue }
    }

    private fun putBooleanValue(store: DataStore<Preferences>, key: String, value: Boolean) {
        val preferenceKey = booleanPreferencesKey(key)
        runBlocking { store.edit { preferences -> preferences[preferenceKey] = value } }
    }

    private fun getIntValue(store: DataStore<Preferences>, key: String, defaultValue: Int): Int {
        val preferenceKey = intPreferencesKey(key)
        return runBlocking { store.data.first()[preferenceKey] ?: defaultValue }
    }

    private fun putIntValue(store: DataStore<Preferences>, key: String, value: Int) {
        val preferenceKey = intPreferencesKey(key)
        runBlocking { store.edit { preferences -> preferences[preferenceKey] = value } }
    }

    private fun getLongValue(store: DataStore<Preferences>, key: String, defaultValue: Long): Long {
        val preferenceKey = longPreferencesKey(key)
        return runBlocking { store.data.first()[preferenceKey] ?: defaultValue }
    }

    private fun putLongValue(store: DataStore<Preferences>, key: String, value: Long) {
        val preferenceKey = longPreferencesKey(key)
        runBlocking { store.edit { preferences -> preferences[preferenceKey] = value } }
    }

    private fun getFloatValue(
        store: DataStore<Preferences>,
        key: String,
        defaultValue: Float,
    ): Float {
        val preferenceKey = floatPreferencesKey(key)
        return runBlocking { store.data.first()[preferenceKey] ?: defaultValue }
    }

    private fun putFloatValue(store: DataStore<Preferences>, key: String, value: Float) {
        val preferenceKey = floatPreferencesKey(key)
        runBlocking { store.edit { preferences -> preferences[preferenceKey] = value } }
    }

    private fun removeKeyValue(store: DataStore<Preferences>, keyName: String) {
        runBlocking {
            store.edit { preferences ->
                val key =
                    preferences.asMap().keys.firstOrNull { existingKey ->
                        existingKey.name == keyName
                    } ?: return@edit
                preferences.remove(key)
            }
        }
    }

    private fun removeKeysByPrefix(store: DataStore<Preferences>, keyPrefixes: Set<String>) {
        runBlocking {
            store.edit { preferences ->
                val keysToRemove =
                    preferences.asMap().keys.filter { key ->
                        keyPrefixes.any { prefix -> key.name.startsWith(prefix) }
                    }
                keysToRemove.forEach { key -> preferences.remove(key) }
            }
        }
    }

    private fun readPreferences(store: DataStore<Preferences>): Preferences {
        return runBlocking { store.data.first() }
    }

    private fun getAllKeyNames(store: DataStore<Preferences>): Set<String> {
        return readPreferences(store).asMap().keys.map { it.name }.toSet()
    }
}
