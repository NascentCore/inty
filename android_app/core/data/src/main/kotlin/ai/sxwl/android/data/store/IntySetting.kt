package ai.sxwl.android.data.store

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.utils.AppUtils
import android.content.Context
import android.os.Handler
import android.os.Looper
import com.tencent.mmkv.MMKV
import java.lang.ref.WeakReference
import kotlin.random.Random
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.Serializable

private const val KEY_RESUB_REMINDER_LAST_TIME = "resub_reminder_last_time"
private const val KEY_RESUB_REMINDER_SHOW_COUNT = "resub_reminder_show_count"
private const val KEY_MESSAGES_TAB_HAS_PUSH = "messages_tab_has_push"
private const val KEY_CONVERSATION_PUSH_PREFIX = "conversation_has_push_"
private const val KEY_PREFIX_EXPLORE_FAVORITE = "explore_favorite_"
private const val KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME = "feedback_dialog_last_show_time"
private const val KEY_IMAGE_FEEDBACK_PROMPT_LAST_LOCAL_DATE =
    "image_feedback_prompt_last_local_date"
private const val KEY_INTELLIMATE_TIP_LAST_SHOW_TIME = "intellimate_tip_last_show_time"

// IntelliMate Tips 展示频率：最多每 8 小时一次（降低打扰）
private const val INTELLIMATE_TIP_MIN_INTERVAL_MILLIS = 8 * 60 * 60 * 1000L

private val Context.intySettingsCache by jsonDataStore("IntySetting", IntySettingsCache())

object IntySetting {
    // 当前UserId
    private var contextRef: WeakReference<Context>? = null

    fun initialize(context: Context) {
        this.contextRef = WeakReference(context)

        runBlocking {
            if (!context.intySettingsCache.data.first().isMigrateFinished) {
                // 初始化 MMKV（必须在所有使用 MMKV 的代码之前）
                // 使用 MKKV 的代码包括：IntySetting, BoostManager, BoostRepository
                MMKV.initialize(context)

                val allUserSetting: MMKV =
                    MMKV.defaultMMKV(MMKV.SINGLE_PROCESS_MODE, AppUtils.getPackageName())
                val curUidFromMmkv = allUserSetting.decodeString("cur_uid") ?: ""
                val curUserSetting =
                    MMKV.mmkvWithID("user_$curUidFromMmkv", MMKV.MULTI_PROCESS_MODE)

                val appData =
                    allUserSetting
                        .allKeys()
                        ?.filter { it.startsWith("app_data_") }
                        ?.mapNotNull { key ->
                            allUserSetting.decodeString(key)?.let {
                                key.removePrefix("app_data_") to it
                            }
                        }
                        ?.toMap() ?: emptyMap()

                val conversationHasPush =
                    curUserSetting
                        .allKeys()
                        ?.filter { it.startsWith(KEY_CONVERSATION_PUSH_PREFIX) }
                        ?.mapNotNull { key ->
                            key.removePrefix(KEY_CONVERSATION_PUSH_PREFIX)
                                .takeIf { it.isNotEmpty() }
                                ?.takeIf { curUserSetting.decodeBool(key, false) }
                                ?.let { it to true }
                        }
                        ?.toMap() ?: emptyMap()
                val exploreFavorite =
                    curUserSetting
                        .allKeys()
                        ?.filter { it.startsWith(KEY_PREFIX_EXPLORE_FAVORITE) }
                        ?.mapNotNull { key ->
                            key.removePrefix(KEY_PREFIX_EXPLORE_FAVORITE)
                                .takeIf { it.isNotBlank() }
                                ?.takeIf { curUserSetting.decodeBool(key, false) }
                                ?.let { it to true }
                        }
                        ?.toMap() ?: emptyMap()
                val conversationPinned =
                    curUserSetting
                        .allKeys()
                        ?.filter { it.startsWith("conversation_pinned_") }
                        ?.mapNotNull { key ->
                            key.removePrefix("conversation_pinned_")
                                .takeIf { it.isNotEmpty() }
                                ?.let { it to curUserSetting.decodeBool(key, false) }
                        }
                        ?.toMap() ?: emptyMap()
                val conversationHidden =
                    curUserSetting
                        .allKeys()
                        ?.filter {
                            it.startsWith("conversation_hidden_") &&
                                !it.startsWith("conversation_hidden_time_")
                        }
                        ?.mapNotNull { key ->
                            key.removePrefix("conversation_hidden_")
                                .takeIf { it.isNotEmpty() }
                                ?.let { it to curUserSetting.decodeBool(key, false) }
                        }
                        ?.toMap() ?: emptyMap()
                val conversationHiddenTime =
                    curUserSetting
                        .allKeys()
                        ?.filter { it.startsWith("conversation_hidden_time_") }
                        ?.mapNotNull { key ->
                            key.removePrefix("conversation_hidden_time_")
                                .takeIf { it.isNotEmpty() }
                                ?.let { it to curUserSetting.decodeLong(key, 0L) }
                        }
                        ?.toMap() ?: emptyMap()
                val userProfile =
                    curUserSetting
                        .allKeys()
                        ?.filter { it.startsWith("user_profile_") }
                        ?.mapNotNull { key ->
                            curUserSetting
                                .decodeString(key)
                                ?.takeIf { it.isNotEmpty() }
                                ?.let { key.removePrefix("user_profile_") to it }
                        }
                        ?.toMap() ?: emptyMap()

                val migrated =
                    IntySettingsCache(
                        isMigrateFinished = true,
                        curUID = curUidFromMmkv,
                        keyboardHeight = allUserSetting.getFloat("keyboardHeight", 0f),
                        showGuest = allUserSetting.decodeBool("show_guest", false),
                        appData = appData,
                        userCache =
                            IntySettingsCache.UserCache(
                                token = curUserSetting.decodeString("token") ?: "",
                                userSetKeepTalking =
                                    curUserSetting.decodeBool("user_set_keep_talking", false),
                                userSetAutoPlayVoice =
                                    curUserSetting.decodeBool("user_set_auto_play_voice", false),
                                vibeModeEnabled =
                                    curUserSetting.decodeBool("vibe_mode_enabled", false),
                                tipsDisabled = curUserSetting.decodeBool("tips_disabled", false),
                                intellimateTipLastShowTimeMillis =
                                    curUserSetting.decodeLong(
                                        KEY_INTELLIMATE_TIP_LAST_SHOW_TIME,
                                        -1L,
                                    ),
                                userSetAutoPlayAnimation =
                                    curUserSetting.decodeBool(
                                        "user_set_auto_play_animation",
                                        false,
                                    ),
                                userSetTextStreaming =
                                    curUserSetting.decodeBool("user_set_text_streaming", false),
                                userSetSceneActionButton =
                                    curUserSetting.decodeBool(
                                        "user_set_scene_action_button",
                                        false,
                                    ),
                                resubReminderLastTime =
                                    curUserSetting.decodeLong(KEY_RESUB_REMINDER_LAST_TIME, 0L),
                                resubReminderShowCount =
                                    curUserSetting.decodeInt(KEY_RESUB_REMINDER_SHOW_COUNT, 0),
                                feedbackDialogLastShowTime =
                                    curUserSetting.decodeLong(
                                        KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME,
                                        -1L,
                                    ),
                                imageFeedbackPromptLastLocalDate =
                                    curUserSetting.decodeString(
                                        KEY_IMAGE_FEEDBACK_PROMPT_LAST_LOCAL_DATE,
                                        "",
                                    ) ?: "",
                                messagesTabHasPush =
                                    curUserSetting.decodeBool(KEY_MESSAGES_TAB_HAS_PUSH, false),
                                conversationHasPush = conversationHasPush,
                                hasAppUpdateTips =
                                    curUserSetting.getBoolean("has_app_update_tips", false),
                                currentSortSeed = curUserSetting.getInt("current_sort_seed", 0),
                                exploreFavorite = exploreFavorite,
                                conversationPinned = conversationPinned,
                                conversationHidden = conversationHidden,
                                conversationHiddenTime = conversationHiddenTime,
                                userProfile = userProfile,
                            ),
                    )
                context.intySettingsCache.updateData { _ -> migrated }
            }
        }
    }

    private fun getIntySettingCache(): IntySettingsCache? {
        return runBlocking { contextRef?.get()?.intySettingsCache?.data?.first() }
    }

    private suspend fun updateIntySetting(update: (IntySettingsCache) -> IntySettingsCache) {
        contextRef?.get()?.intySettingsCache?.updateData(update)
    }

    /** 仅用于测试：将 DataStore 重置为默认状态并标记已迁移，以便 initialize 不触发 MMKV 迁移。 */
    internal fun resetCacheForTest(context: Context) {
        runBlocking {
            context.intySettingsCache.updateData { _ ->
                IntySettingsCache(isMigrateFinished = true)
            }
        }
    }

    //    private fun getUserDataStore(): Flow<DataStore<Preferences>> {
    //        return getCurUserIDFlow().map { dataStore("user_$it") }
    //    }
    //
    //    fun getCurUserIDFlow(): Flow<String> {
    //        return dataStore().data.map { it[STORE_KEY_CUR_UID] ?: getCurUserID() }
    //    }
    //
    //    fun getTokenFlow(): Flow<String> {
    //        return getUserDataStore().flatMapLatest {
    //            it.data.map { data -> data[STORE_KEY_TOKEN] ?: getCurToken()}
    //        }
    //    }

    fun isLoginFlow(): Flow<Boolean> {
        return contextRef?.get()?.intySettingsCache?.data?.map {
            it.curUID.isNotBlank() && it.userCache.token.isNotBlank()
        } ?: flowOf(false)
    }

    fun getCurUserID(): String {
        // return allUserSetting.decodeString("cur_uid") ?: ""
        return getIntySettingCache()?.curUID ?: ""
    }

    /** 切换用户 对应Guest登录Google账户 Google账户退出登录，到Guest账户 */
    suspend fun changeUser(uid: String) {
        // curUid = uid
        // curUserSetting = MMKV.mmkvWithID("user_$curUid", MMKV.MULTI_PROCESS_MODE)
        // allUserSetting.putString("cur_uid", uid)
        // dataStore().edit { it[STORE_KEY_CUR_UID] = uid }
        updateIntySetting { it.copy(curUID = uid) }
        IntySettingsDataStore.onUserChanged()
    }

    suspend fun setToken(token: String) {
        // getUserDataStore().first().edit { it[STORE_KEY_TOKEN] = token }
        updateIntySetting { it.copy(userCache = it.userCache.copy(token = token)) }
    }

    fun getCurToken(): String {
        // return curUserSetting.decodeString("token") ?: ""
        return getIntySettingCache()?.userCache?.token ?: ""
    }

    fun isLogin(): Boolean {
        return getIntySettingCache()?.let {
            it.curUID.isNotBlank() && it.userCache.token.isNotBlank()
        } ?: false
    }

    suspend fun isLoginSuspend(): Boolean {
        return contextRef?.get()?.intySettingsCache?.data?.first()?.let {
            it.curUID.isNotBlank() && it.userCache.token.isNotBlank()
        } ?: false
    }

    /** 登录接口后，本地处理登录业务的数据逻辑 */
    suspend fun login(uid: String, token: String) {
        NetServiceMgr.clearCache()

        // 然后更新token
        changeUser(uid)
        setToken(token)

        // 再次清除缓存，确保后续请求使用更新后的认证信息
        NetServiceMgr.clearCache()
    }

    suspend fun setKeyboardHeight(height: Float) {
        updateIntySetting { it.copy(keyboardHeight = height) }
    }

    fun keyboardHeightFlow(): Flow<Float> {
        return contextRef?.get()?.intySettingsCache?.data?.map { it.keyboardHeight } ?: flowOf(0f)
    }

    /** 记录是否显示keepTalking按钮（全局设置） */
    fun setShowKeepTalking(show: Boolean) {
        IntySettingsDataStore.setShowKeepTalking(getCurUserID(), show)
    }

    fun isShowKeepTalking(): Boolean {
        return IntySettingsDataStore.getShowKeepTalking(getCurUserID())
    }

    /** 检查用户是否手动设置过 Keep Talking（用于判断是否使用 Remote Config 默认值） */
    suspend fun hasUserSetKeepTalking(): Boolean {
        return contextRef?.get()?.intySettingsCache?.data?.first()?.userCache?.userSetKeepTalking
            ?: false
    }

    /** 标记用户已手动设置过 Keep Talking */
    suspend fun markUserSetKeepTalking() {
        updateIntySetting { it.copy(userCache = it.userCache.copy(userSetKeepTalking = true)) }
    }

    /** 自动播放语音消息（全局设置，默认开启） */
    fun setAutoPlayAudio(play: Boolean) {
        IntySettingsDataStore.setAutoPlayAudio(getCurUserID(), play)
    }

    fun isAutoPlayAudio(): Boolean {
        return IntySettingsDataStore.getAutoPlayAudio(getCurUserID())
    }

    /** 检查用户是否手动设置过 Auto Play Voice（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetAutoPlayVoice(): Boolean {
        return getIntySettingCache()?.userCache?.userSetAutoPlayVoice ?: false
    }

    /** 标记用户已手动设置过 Auto Play Voice */
    suspend fun markUserSetAutoPlayVoice() {
        updateIntySetting { it.copy(userCache = it.userCache.copy(userSetAutoPlayVoice = true)) }
    }

    /** 自动播放背景动画（全局设置，默认开启） */
    fun setAutoPlayAnimation(enabled: Boolean) {
        IntySettingsDataStore.setAutoPlayAnimation(getCurUserID(), enabled)
    }

    /** 流式显示聊天消息 */
    fun setTextStreaming(enabled: Boolean) {
        IntySettingsDataStore.setTextStreaming(getCurUserID(), enabled)
    }

    fun isAutoPlayAnimation(): Boolean {
        return IntySettingsDataStore.getAutoPlayAnimation(getCurUserID())
    }

    /** 是否流式显示聊天消息 */
    fun isTextStreaming(): Boolean {
        return IntySettingsDataStore.getTextStreaming(getCurUserID())
    }

    /** Vibe Mode 开关状态（仅限订阅用户） */
    fun setVibeModeEnabled(enabled: Boolean) {
        runBlocking { setVibeModeEnabledSuspend(enabled) }
    }

    suspend fun setVibeModeEnabledSuspend(enabled: Boolean) {
        updateIntySetting { it.copy(userCache = it.userCache.copy(vibeModeEnabled = enabled)) }
    }

    fun isVibeModeEnabled(): Boolean {
        return getIntySettingCache()?.userCache?.vibeModeEnabled ?: false
    }

    suspend fun isVibeModeEnabledSuspend(): Boolean {
        return contextRef
            ?.get()
            ?.intySettingsCache
            ?.data
            ?.first()
            ?.userCache
            ?.vibeModeEnabled ?: false
    }

    /** 禁用 IntelliMate tips 弹窗（用户偏好设置） */
    fun setTipsDisabled(disabled: Boolean) {
        runBlocking { setTipsDisabledSuspend(disabled) }
    }

    suspend fun setTipsDisabledSuspend(disabled: Boolean) {
        updateIntySetting { it.copy(userCache = it.userCache.copy(tipsDisabled = disabled)) }
    }

    fun isTipsDisabled(): Boolean {
        return getIntySettingCache()?.userCache?.tipsDisabled ?: false
    }

    suspend fun isTipsDisabledSuspend(): Boolean {
        return contextRef
            ?.get()
            ?.intySettingsCache
            ?.data
            ?.first()
            ?.userCache
            ?.tipsDisabled ?: false
    }

    /** 标记用户已手动设置过 Auto Play Animation */
    fun markUserSetAutoPlayAnimation() {
        runBlocking { markUserSetAutoPlayAnimationSuspend() }
    }

    suspend fun markUserSetAutoPlayAnimationSuspend() {
        updateIntySetting {
            it.copy(userCache = it.userCache.copy(userSetAutoPlayAnimation = true))
        }
    }

    /** 标记用户已手动设置过 Text Streaming */
    fun markUserTextStreaming() {
        runBlocking { markUserTextStreamingSuspend() }
    }

    suspend fun markUserTextStreamingSuspend() {
        updateIntySetting {
            it.copy(userCache = it.userCache.copy(userSetTextStreaming = true))
        }
    }

    /** 显示场景动作输入按钮（全局设置，默认关闭） */
    fun setShowSceneActionButton(show: Boolean) {
        IntySettingsDataStore.setShowSceneActionButton(getCurUserID(), show)
    }

    fun isShowSceneActionButton(): Boolean {
        return IntySettingsDataStore.getShowSceneActionButton(getCurUserID())
    }

    /** 发送 UX/UI gesture signals（全局设置，默认关闭） */
    fun setSendUxUiGestureSignals(enabled: Boolean) {
        IntySettingsDataStore.setSendUxUiGestureSignals(getCurUserID(), enabled)
    }

    fun isSendUxUiGestureSignals(): Boolean {
        return IntySettingsDataStore.getSendUxUiGestureSignals(getCurUserID())
    }

    /** 标记用户已手动设置过 Show Scene Action Button */
    suspend fun markUserSetSceneActionButton() {
        updateIntySetting {
            it.copy(userCache = it.userCache.copy(userSetSceneActionButton = true))
        }
    }

    /** 消息列表是否全屏（全局设置，默认关闭） */
    fun setChatListFullScreen(fullScreen: Boolean) {
        IntySettingsDataStore.setChatListFullScreen(getCurUserID(), fullScreen)
    }

    fun isChatListFullScreen(): Boolean {
        return IntySettingsDataStore.getChatListFullScreen(getCurUserID())
    }

    /** 聊天消息字体大小（单位 sp，默认 14f） */
    fun setChatFontSizeSp(size: Float) {
        IntySettingsDataStore.setChatFontSizeSp(getCurUserID(), size)
    }

    fun getChatFontSizeSp(): Float {
        return IntySettingsDataStore.getChatFontSizeSp(getCurUserID())
    }

    /** 聊天模型选择（全局设置，默认 Gemini 3 Flash） */
    fun setChatModelId(modelId: String) {
        IntySettingsDataStore.setChatModelId(getCurUserID(), modelId)
    }

    fun getChatModelId(): String {
        return IntySettingsDataStore.getChatModelId(getCurUserID())
    }

    fun getLastResubReminderDialogShowTime(): Long {
        return getIntySettingCache()?.userCache?.resubReminderLastTime ?: 0L
    }

    fun setLastResubReminderDialogShowTime(timestampSeconds: Long) {
        runBlocking {
            updateIntySetting {
                it.copy(userCache = it.userCache.copy(resubReminderLastTime = timestampSeconds))
            }
        }
    }

    fun getResubReminderDialogShowCount(): Int {
        return getIntySettingCache()?.userCache?.resubReminderShowCount ?: 0
    }

    fun setResubReminderDialogShowCount(count: Int) {
        runBlocking { setResubReminderDialogShowCountSuspend(count) }
    }

    suspend fun setResubReminderDialogShowCountSuspend(count: Int) {
        updateIntySetting {
            it.copy(userCache = it.userCache.copy(resubReminderShowCount = count))
        }
    }

    fun getFeedbackDialogLastShowTime(): Long {
        return getIntySettingCache()?.userCache?.feedbackDialogLastShowTime ?: -1L
    }

    suspend fun getFeedbackDialogLastShowTimeSuspend(): Long {
        return contextRef
            ?.get()
            ?.intySettingsCache
            ?.data
            ?.first()
            ?.userCache
            ?.feedbackDialogLastShowTime ?: -1L
    }

    fun setFeedbackDialogLastShowTime(timestampMillis: Long) {
        runBlocking { setFeedbackDialogLastShowTimeSuspend(timestampMillis) }
    }

    suspend fun setFeedbackDialogLastShowTimeSuspend(timestampMillis: Long) {
        updateIntySetting {
            it.copy(userCache = it.userCache.copy(feedbackDialogLastShowTime = timestampMillis))
        }
    }

    fun getImageFeedbackPromptLastLocalDate(): String {
        return getIntySettingCache()?.userCache?.imageFeedbackPromptLastLocalDate.orEmpty()
    }

    suspend fun getImageFeedbackPromptLastLocalDateSuspend(): String {
        return contextRef
            ?.get()
            ?.intySettingsCache
            ?.data
            ?.first()
            ?.userCache
            ?.imageFeedbackPromptLastLocalDate.orEmpty()
    }

    suspend fun setImageFeedbackPromptLastLocalDate(localDateKey: String) {
        updateIntySetting {
            it.copy(
                userCache =
                    it.userCache.copy(imageFeedbackPromptLastLocalDate = localDateKey.trim())
            )
        }
    }

    /** 记录消息Tab是否需要显示推送红点（须在协程中调用，勿在主线程配合 runBlocking） */
    suspend fun setMessagesTabHasPushSuspend(hasPush: Boolean) {
        updateIntySetting { it.copy(userCache = it.userCache.copy(messagesTabHasPush = hasPush)) }
    }

    fun hasMessagesTabPush(): Boolean {
        return getIntySettingCache()?.userCache?.messagesTabHasPush ?: false
    }

    /** 记录特定会话是否有推送未读 */
    fun setConversationHasPush(agentId: String, hasPush: Boolean) {
        runBlocking { setConversationHasPushSuspend(agentId, hasPush) }
    }

    suspend fun setConversationHasPushSuspend(agentId: String, hasPush: Boolean) {
        updateIntySetting {
            it.copy(
                userCache =
                    it.userCache.copy(
                        conversationHasPush =
                            it.userCache.conversationHasPush.toMutableMap().also { map ->
                                if (hasPush) map[agentId] = true else map.remove(agentId)
                            }
                    )
            )
        }
    }

    fun hasConversationPush(agentId: String): Boolean {
        return getIntySettingCache()?.userCache?.conversationHasPush?.get(agentId) == true
    }

    suspend fun hasConversationPushSuspend(agentId: String): Boolean {
        return contextRef
            ?.get()
            ?.intySettingsCache
            ?.data
            ?.first()
            ?.userCache
            ?.conversationHasPush
            ?.get(agentId) == true
    }

    // 标记是否已经有可用的App更新，用于红点标记
    fun hasAppUpdateTips(): Boolean {
        return getIntySettingCache()?.userCache?.hasAppUpdateTips ?: false
    }

    suspend fun hasAppUpdateTipsSuspend(): Boolean {
        return contextRef
            ?.get()
            ?.intySettingsCache
            ?.data
            ?.first()
            ?.userCache
            ?.hasAppUpdateTips ?: false
    }

    fun setAppUpdateTips(showed: Boolean) {
        runBlocking { setAppUpdateTipsSuspend(showed) }
    }

    suspend fun setAppUpdateTipsSuspend(showed: Boolean) {
        updateIntySetting { it.copy(userCache = it.userCache.copy(hasAppUpdateTips = showed)) }
    }

    private var isLoggingOut = false

    fun logout() {
        isLoggingOut = true
        runBlocking { setToken("") }
        // 延迟重置标志，确保401处理器有时间识别
        Handler(Looper.getMainLooper()).postDelayed({ isLoggingOut = false }, 2000)
    }

    fun isLoggingOut(): Boolean {
        return isLoggingOut
    }

    // 用于推荐接口后端sort随机排序的seed种子
    fun sortSeed(): Int {
        return getIntySettingCache()?.userCache?.currentSortSeed ?: 0
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
        runBlocking {
            updateIntySetting { it.copy(userCache = it.userCache.copy(currentSortSeed = seed)) }
        }
    }

    // region 通用的用户信息存储方法（不依赖具体的 UserProfile 类）
    fun setUserProfileData(key: String, value: String) {
        // curUserSetting.putString("user_profile_$key", value)
        runBlocking {
            // getUserDataStore().first().putString("user_profile_$key", value)
            updateIntySetting {
                it.copy(
                    userCache =
                        it.userCache.copy(
                            userProfile =
                                it.userCache.userProfile.toMutableMap().also { map ->
                                    map[key] = value
                                }
                        )
                )
            }
        }
    }

    suspend fun setUserProfileDataSuspend(key: String, value: String) {
        updateIntySetting {
            it.copy(
                userCache =
                    it.userCache.copy(
                        userProfile =
                            it.userCache.userProfile.toMutableMap().also { map -> map[key] = value }
                    )
            )
        }
    }

    fun getUserProfileData(key: String): String? {
        // return curUserSetting.decodeString("user_profile_$key")
        //        return runBlocking {
        //            getUserDataStore().first().getString("user_profile_$key").first()
        //        }
        return getIntySettingCache()?.userCache?.userProfile?.get(key)
    }

    fun clearUserProfileData(key: String) {
        // curUserSetting.removeValueForKey("user_profile_$key")
        runBlocking {
            updateIntySetting {
                it.copy(
                    userCache =
                        it.userCache.copy(
                            userProfile =
                                it.userCache.userProfile.toMutableMap().also { map ->
                                    map.remove(key)
                                }
                        )
                )
            }
        }
    }

    fun hasShowGuest(): Boolean {
        return getIntySettingCache()?.showGuest ?: false
    }

    fun setShowGuested() {
        runBlocking { updateIntySetting { it.copy(showGuest = true) } }
    }

    // region 应用级别的通用存储方法（不依赖用户）
    /** 设置应用级别的数据（所有用户共享） */
    fun setAppData(key: String, value: String) {
        runBlocking {
            updateIntySetting {
                it.copy(appData = it.appData.toMutableMap().also { map -> map[key] = value })
            }
        }
    }

    /** 获取应用级别的数据 */
    fun getAppData(key: String): String? {
        return getIntySettingCache()?.appData?.get(key)
    }

    /** 清除应用级别的数据 */
    fun clearAppData(key: String) {
        runBlocking {
            updateIntySetting {
                it.copy(appData = it.appData.toMutableMap().also { map -> map.remove(key) })
            }
        }
    }

    /** 获取所有应用级别的数据键（用于批量操作） */
    fun getAllAppDataKeys(): Set<String> {
        return getIntySettingCache()?.appData?.keys ?: emptySet()
    }

    // endregion

    // region Explore收藏状态

    /** 设置 Explore 页面角色卡的收藏状态 */
    fun setExploreAgentFavorite(agentId: String, favorite: Boolean) {
        if (agentId.isBlank()) return
        runBlocking {
            updateIntySetting {
                it.copy(
                    userCache =
                        it.userCache.copy(
                            exploreFavorite =
                                it.userCache.exploreFavorite.toMutableMap().also { map ->
                                    if (favorite) map[agentId] = true else map.remove(agentId)
                                }
                        )
                )
            }
        }
    }

    /** 获取 Explore 页面角色卡的收藏状态 */
    fun isExploreAgentFavorite(agentId: String): Boolean {
        if (agentId.isBlank()) return false
        return getIntySettingCache()?.userCache?.exploreFavorite?.get(agentId) == true
    }

    /** 获取所有已收藏的 Explore 角色ID */
    fun getExploreFavoriteAgentIds(): List<String> {
        val fromCache = getIntySettingCache()?.userCache?.exploreFavorite ?: return emptyList()
        return fromCache.filter { it.value }.keys.sorted()
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

    // endregion

    // region 会话Pin/Hide相关设置
    /** 设置会话置顶状态 */
    fun setConversationPinned(agentId: String, pinned: Boolean) {
        // curUserSetting.putBoolean("conversation_pinned_$agentId", pinned)
        //        runBlocking {
        //            getUserDataStore().first().putBoolean("conversation_pinned_$agentId", pinned)
        //        }
        runBlocking {
            updateIntySetting {
                it.copy(
                    userCache =
                        it.userCache.copy(
                            conversationPinned =
                                it.userCache.conversationPinned.toMutableMap().also { map ->
                                    map[agentId] = pinned
                                }
                        )
                )
            }
        }
    }

    /** 获取会话置顶状态 */
    fun isConversationPinned(agentId: String): Boolean {
        // return curUserSetting.decodeBool("conversation_pinned_$agentId", false)
        //        return runBlocking {
        //            getUserDataStore().first().getBoolean("conversation_pinned_$agentId").first()
        // ?: false
        //        }
        return getIntySettingCache()?.userCache?.conversationPinned?.get(agentId) ?: false
    }

    /** 设置会话隐藏状态 */
    fun setConversationHidden(agentId: String, hidden: Boolean) {
        //        curUserSetting.putBoolean("conversation_hidden_$agentId", hidden)
        //        if (hidden) {
        //            // 记录隐藏时的时间戳，用于判断是否有新消息
        //            curUserSetting.putLong("conversation_hidden_time_$agentId",
        // System.currentTimeMillis())
        //        } else {
        //            curUserSetting.removeValueForKey("conversation_hidden_time_$agentId")
        //        }
        //        runBlocking {
        //            getUserDataStore().first().let {
        //                it.putBoolean("conversation_hidden_$agentId", hidden)
        //
        //                // 记录隐藏时的时间戳，用于判断是否有新消息
        //                it.putLong(
        //                    "conversation_hidden_time_$agentId",
        //                    if (hidden) System.currentTimeMillis() else 0L
        //                )
        //            }
        //        }
        runBlocking {
            updateIntySetting {
                it.copy(
                    userCache =
                        it.userCache.copy(
                            conversationHidden =
                                it.userCache.conversationHidden.toMutableMap().also { map ->
                                    map[agentId] = hidden
                                },
                            conversationHiddenTime =
                                it.userCache.conversationHiddenTime.toMutableMap().also { map ->
                                    map[agentId] = if (hidden) System.currentTimeMillis() else 0L
                                },
                        )
                )
            }
        }
    }

    /** 获取会话隐藏状态 */
    fun isConversationHidden(agentId: String): Boolean {
        // return curUserSetting.decodeBool("conversation_hidden_$agentId", false)
        //        return runBlocking {
        //            getUserDataStore().flatMapLatest { userDataStore ->
        //                userDataStore.getBoolean("conversation_hidden_$agentId")
        //            }.first() ?: false
        //        }
        return getIntySettingCache()?.userCache?.conversationHidden?.get(agentId) ?: false
    }

    /** 获取会话隐藏时间（用于判断是否应该恢复显示） */
    fun getConversationHiddenTime(agentId: String): Long {
        // return curUserSetting.decodeLong("conversation_hidden_time_$agentId", 0L)
        //        return runBlocking {
        //            getUserDataStore().flatMapLatest { userDataStore ->
        //                userDataStore.getLong("conversation_hidden_time_$agentId")
        //            }.first() ?: 0L
        //        }
        return getIntySettingCache()?.userCache?.conversationHiddenTime?.get(agentId) ?: 0L
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

@Serializable
data class IntySettingsCache(
    val isMigrateFinished: Boolean = false,
    val curUID: String = "",
    val userCache: UserCache = UserCache(),
    val keyboardHeight: Float = 0f,
    val showGuest: Boolean = false,
    val appData: Map<String, String> = emptyMap(),
) {
    @Serializable
    data class UserCache(
        val token: String = "",
        val conversationHiddenTime: Map<String, Long> = emptyMap(),
        val conversationHidden: Map<String, Boolean> = emptyMap(),
        val conversationPinned: Map<String, Boolean> = emptyMap(),
        val userProfile: Map<String, String> = emptyMap(),
        val userSetKeepTalking: Boolean = false,
        val userSetAutoPlayVoice: Boolean = false,
        val vibeModeEnabled: Boolean = false,
        val tipsDisabled: Boolean = false,
        val intellimateTipLastShowTimeMillis: Long = -1L,
        val userSetAutoPlayAnimation: Boolean = false,
        val userSetTextStreaming: Boolean = false,
        val userSetSceneActionButton: Boolean = false,
        val resubReminderLastTime: Long = 0L,
        val resubReminderShowCount: Int = 0,
        val feedbackDialogLastShowTime: Long = -1L,
        val imageFeedbackPromptLastLocalDate: String = "",
        val messagesTabHasPush: Boolean = false,
        val conversationHasPush: Map<String, Boolean> = emptyMap(),
        val hasAppUpdateTips: Boolean = false,
        val currentSortSeed: Int = 0,
        val exploreFavorite: Map<String, Boolean> = emptyMap(),
    )
}
