package ai.sxwl.android.data.store

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.utils.AppUtils
import android.os.Handler
import android.os.Looper
import com.tencent.mmkv.MMKV
import kotlin.random.Random

private const val KEY_RESUB_REMINDER_LAST_TIME = "resub_reminder_last_time"
private const val KEY_RESUB_REMINDER_SHOW_COUNT = "resub_reminder_show_count"
private const val KEY_CHAT_FONT_SIZE_SP = "chat_font_size_sp"
private const val KEY_MESSAGES_TAB_HAS_PUSH = "messages_tab_has_push"
private const val KEY_CONVERSATION_PUSH_PREFIX = "conversation_has_push_"
private const val DEFAULT_CHAT_FONT_SIZE_SP = 14f
private const val KEY_PREFIX_EXPLORE_FAVORITE = "explore_favorite_"
private const val KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME = "feedback_dialog_last_show_time"
private const val KEY_FEEDBACK_REQUESTED = "feedback_requested"
private const val KEY_TOTAL_MESSAGE_COUNT = "total_message_count"

object IntySetting {

    // App级通用标记的存储 使用的对象
    // MKKV.initialize(app) 已经在 IntelliMateApp.onCreate() 中调用
    private val allUserSetting: MMKV =
        MMKV.defaultMMKV(MMKV.SINGLE_PROCESS_MODE, AppUtils.getPackageName())

    // 当前用户级别的数据存储
    private var curUserSetting: MMKV

    // 当前UserId
    private var curUid: String = ""

    // 用于同步 incrementTotalMessageCount 操作的锁对象
    private val messageCountLock = Any()

    // 用于同步反馈请求标记操作的锁对象
    private val feedbackRequestLock = Any()

    init {

        curUid = getCurUserID()
        curUserSetting = MMKV.mmkvWithID("user_$curUid", MMKV.MULTI_PROCESS_MODE)
    }

    fun getCurUserID(): String {
        return allUserSetting.decodeString("cur_uid") ?: ""
    }

    /** 切换用户 对应Guest登录Google账户 Google账户退出登录，到Guest账户 */
    fun changeUser(uid: String) {
        curUserSetting

        curUid = uid
        curUserSetting = MMKV.mmkvWithID("user_$curUid", MMKV.MULTI_PROCESS_MODE)
        allUserSetting.putString("cur_uid", uid)
    }

    fun setToken(token: String) {
        curUserSetting.putString("token", token)
    }

    fun getCurToken(): String {
        return curUserSetting.decodeString("token") ?: ""
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

    /** 记录是否显示keepTalking按钮（全局设置） */
    fun setShowKeepTalking(show: Boolean) {
        curUserSetting.putBoolean("show_keep_talking", show)
    }

    fun isShowKeepTalking(): Boolean {
        return curUserSetting.decodeBool("show_keep_talking", false)
    }

    /** 检查用户是否手动设置过 Keep Talking（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetKeepTalking(): Boolean {
        return curUserSetting.decodeBool("user_set_keep_talking", false)
    }

    /** 标记用户已手动设置过 Keep Talking */
    fun markUserSetKeepTalking() {
        curUserSetting.putBoolean("user_set_keep_talking", true)
    }

    /** 自动播放语音消息（全局设置，默认开启） */
    fun setAutoPlayAudio(play: Boolean) {
        curUserSetting.putBoolean("auto_play_audio", play)
    }

    fun isAutoPlayAudio(): Boolean {
        // 默认值为true（开启）
        return curUserSetting.decodeBool("auto_play_audio", true)
    }

    /** 检查用户是否手动设置过 Auto Play Voice（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetAutoPlayVoice(): Boolean {
        return curUserSetting.decodeBool("user_set_auto_play_voice", false)
    }

    /** 标记用户已手动设置过 Auto Play Voice */
    fun markUserSetAutoPlayVoice() {
        curUserSetting.putBoolean("user_set_auto_play_voice", true)
    }

    /** 自动播放背景动画（全局设置，默认开启） */
    fun setAutoPlayAnimation(enabled: Boolean) {
        curUserSetting.putBoolean("auto_play_animation", enabled)
    }

    /** 流式显示聊天消息 */
    fun setTextStreaming(enabled: Boolean) {
        curUserSetting.putBoolean("text_streaming", enabled)
    }

    fun isAutoPlayAnimation(): Boolean {
        return curUserSetting.decodeBool("auto_play_animation", true)
    }

    /** 是否流式显示聊天消息 */
    fun isTextStreaming(): Boolean {
        return curUserSetting.decodeBool("text_streaming", true)
    }

    /** 检查用户是否手动设置过 Auto Play Animation */
    fun hasUserSetAutoPlayAnimation(): Boolean {
        return curUserSetting.decodeBool("user_set_auto_play_animation", false)
    }

    /** 标记用户已手动设置过 Auto Play Animation */
    fun markUserSetAutoPlayAnimation() {
        curUserSetting.putBoolean("user_set_auto_play_animation", true)
    }

    /** 标记用户已手动设置过 Text Streaming*/
    fun markUserTextStreaming() {
        curUserSetting.putBoolean("user_set_text_streaming", true)
    }

    /** 显示场景动作输入按钮（全局设置，默认关闭） */
    fun setShowSceneActionButton(show: Boolean) {
        curUserSetting.putBoolean("show_scene_action_button", show)
    }

    fun isShowSceneActionButton(): Boolean {
        // 默认值为false（关闭）
        return curUserSetting.decodeBool("show_scene_action_button", false)
    }

    /** 检查用户是否手动设置过 Show Scene Action Button（用于判断是否使用 Remote Config 默认值） */
    fun hasUserSetSceneActionButton(): Boolean {
        return curUserSetting.decodeBool("user_set_scene_action_button", false)
    }

    /** 标记用户已手动设置过 Show Scene Action Button */
    fun markUserSetSceneActionButton() {
        curUserSetting.putBoolean("user_set_scene_action_button", true)
    }

    /** 聊天消息字体大小（单位 sp，默认 14f） */
    fun setChatFontSizeSp(size: Float) {
        curUserSetting.putFloat(KEY_CHAT_FONT_SIZE_SP, size)
    }

    fun getChatFontSizeSp(): Float {
        return curUserSetting.decodeFloat(KEY_CHAT_FONT_SIZE_SP, DEFAULT_CHAT_FONT_SIZE_SP)
    }

    fun getLastResubReminderDialogShowTime(): Long {
        return curUserSetting.decodeLong(KEY_RESUB_REMINDER_LAST_TIME, 0L)
    }

    fun setLastResubReminderDialogShowTime(timestampSeconds: Long) {
        curUserSetting.putLong(KEY_RESUB_REMINDER_LAST_TIME, timestampSeconds)
    }

    fun getResubReminderDialogShowCount(): Int {
        return curUserSetting.decodeInt(KEY_RESUB_REMINDER_SHOW_COUNT, 0)
    }

    fun setResubReminderDialogShowCount(count: Int) {
        curUserSetting.putInt(KEY_RESUB_REMINDER_SHOW_COUNT, count)
    }

    fun getFeedbackDialogLastShowTime(): Long {
        return curUserSetting.decodeLong(KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME, 0L)
    }

    fun setFeedbackDialogLastShowTime(timestampMillis: Long) {
        curUserSetting.putLong(KEY_FEEDBACK_DIALOG_LAST_SHOW_TIME, timestampMillis)
    }

    /** 获取是否已请求过反馈 */
    fun get_feedback_requested(): Boolean {
        return curUserSetting.decodeBool(KEY_FEEDBACK_REQUESTED, false)
    }

    /** 设置是否已请求过反馈 */
    fun set_feedback_requested(value: Boolean) {
        curUserSetting.putBoolean(KEY_FEEDBACK_REQUESTED, value)
    }

    /**
     * 原子性地尝试标记反馈为已请求
     *
     * 如果反馈尚未被请求，则标记为已请求并返回 true。 如果反馈已被请求，则返回 false。
     *
     * 此方法使用同步锁确保原子性，防止并发调用时出现竞态条件。 这对于防止多个触发点（如 ChatViewModel 和 HomeScreen）同时显示反馈对话框至关重要。
     *
     * @return true 如果成功标记为已请求（之前未请求），false 如果已经被请求过
     */
    fun tryMarkFeedbackRequested(): Boolean {
        synchronized(feedbackRequestLock) {
            if (get_feedback_requested()) {
                return false
            }
            set_feedback_requested(true)
            return true
        }
    }

    /** 获取总消息数（跨所有AI角色） */
    fun getTotalMessageCount(): Int {
        return curUserSetting.decodeInt(KEY_TOTAL_MESSAGE_COUNT, 0)
    }

    /**
     * 增加总消息数并返回新的计数
     *
     * 使用同步锁确保读-改-写操作的原子性，防止并发调用时丢失增量。 这对于反馈对话框触发逻辑至关重要，因为它依赖于消息计数达到100的倍数。
     */
    fun incrementTotalMessageCount(): Int {
        synchronized(messageCountLock) {
            // TODO: DataStore 是否能提供同步？
            val currentCount = getTotalMessageCount()
            val newCount = currentCount + 1
            curUserSetting.putInt(KEY_TOTAL_MESSAGE_COUNT, newCount)
            return newCount
        }
    }

    /** 记录消息Tab是否需要显示推送红点 */
    fun setMessagesTabHasPush(hasPush: Boolean) {
        curUserSetting.putBoolean(KEY_MESSAGES_TAB_HAS_PUSH, hasPush)
    }

    fun hasMessagesTabPush(): Boolean {
        return curUserSetting.decodeBool(KEY_MESSAGES_TAB_HAS_PUSH, false)
    }

    /** 记录特定会话是否有推送未读 */
    fun setConversationHasPush(agentId: String, hasPush: Boolean) {
        val key = "$KEY_CONVERSATION_PUSH_PREFIX$agentId"
        if (hasPush) {
            curUserSetting.putBoolean(key, true)
        } else {
            curUserSetting.removeValueForKey(key)
        }
    }

    fun hasConversationPush(agentId: String): Boolean {
        return curUserSetting.decodeBool("$KEY_CONVERSATION_PUSH_PREFIX$agentId", false)
    }

    // 标记是否已经有可用的App更新，用于红点标记
    fun hasAppUpdateTips(): Boolean {
        return curUserSetting.getBoolean("has_app_update_tips", false)
    }

    fun setAppUpdateTips(showed: Boolean) {
        curUserSetting.putBoolean("has_app_update_tips", showed)
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
        return curUserSetting.getInt("current_sort_seed", 0)
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
        curUserSetting.putInt("current_sort_seed", seed)
    }

    // region 通用的用户信息存储方法（不依赖具体的 UserProfile 类）
    fun setUserProfileData(key: String, value: String) {
        curUserSetting.putString("user_profile_$key", value)
    }

    fun getUserProfileData(key: String): String? {
        return curUserSetting.decodeString("user_profile_$key")
    }

    fun setUserProfileBoolean(key: String, value: Boolean) {
        curUserSetting.putBoolean("user_profile_$key", value)
    }

    fun getUserProfileBoolean(key: String, defaultValue: Boolean = false): Boolean {
        return curUserSetting.decodeBool("user_profile_$key", defaultValue)
    }

    fun setUserProfileInt(key: String, value: Int) {
        curUserSetting.putInt("user_profile_$key", value)
    }

    fun getUserProfileInt(key: String, defaultValue: Int = 0): Int {
        return curUserSetting.decodeInt("user_profile_$key", defaultValue)
    }

    fun hasUserProfileData(key: String): Boolean {
        return curUserSetting.decodeString("user_profile_$key")?.isNotEmpty() == true
    }

    fun clearUserProfileData(key: String) {
        curUserSetting.removeValueForKey("user_profile_$key")
    }

    fun clearAllUserProfileData() {
        // 清除所有以 user_profile_ 开头的键
        val keys = curUserSetting.allKeys()
        keys?.forEach { key ->
            if (key.startsWith("user_profile_")) {
                curUserSetting.removeValueForKey(key)
            }
        }
    }

    fun hasShowGuest(): Boolean {
        return allUserSetting.decodeBool("show_guest", false)
    }

    fun setShowGuested() {
        allUserSetting.putBoolean("show_guest", true)
    }

    // region 应用级别的通用存储方法（不依赖用户）
    /** 设置应用级别的数据（所有用户共享） */
    fun setAppData(key: String, value: String) {
        allUserSetting.putString("app_data_$key", value)
    }

    /** 获取应用级别的数据 */
    fun getAppData(key: String): String? {
        return allUserSetting.decodeString("app_data_$key")
    }

    /** 检查应用级别的数据是否存在 */
    fun hasAppData(key: String): Boolean {
        return allUserSetting.decodeString("app_data_$key")?.isNotEmpty() == true
    }

    /** 清除应用级别的数据 */
    fun clearAppData(key: String) {
        allUserSetting.removeValueForKey("app_data_$key")
    }

    /** 获取所有应用级别的数据键（用于批量操作） */
    fun getAllAppDataKeys(): Set<String> {
        val allKeys = allUserSetting.allKeys()
        return allKeys?.filter { it.startsWith("app_data_") }?.toSet() ?: emptySet()
    }

    // endregion

    // endregion

    // region 聊天数据持久化相关方法

    /** 清除指定agent的聊天数据（清理可能存在的旧数据） */
    fun clearChatData(agentId: String) {
        curUserSetting.removeValueForKey("chat_messages_$agentId")
        curUserSetting.removeValueForKey("chat_offset_$agentId")
        curUserSetting.removeValueForKey("chat_has_more_$agentId")
        curUserSetting.removeValueForKey("chat_initial_loaded_$agentId")
    }

    /** 清除所有聊天数据 */
    fun clearAllChatData() {
        val keys = curUserSetting.allKeys()
        keys?.forEach { key: String ->
            if (
                key.startsWith("chat_messages_") ||
                    key.startsWith("chat_offset_") ||
                    key.startsWith("chat_has_more_") ||
                    key.startsWith("chat_initial_loaded_")
            ) {
                curUserSetting.removeValueForKey(key)
            }
        }
    }

    // endregion

    // region Explore收藏状态

    /** 设置 Explore 页面角色卡的收藏状态 */
    fun setExploreAgentFavorite(agentId: String, favorite: Boolean) {
        if (agentId.isBlank()) return
        val key = "$KEY_PREFIX_EXPLORE_FAVORITE$agentId"
        if (favorite) {
            curUserSetting.putBoolean(key, true)
        } else {
            curUserSetting.removeValueForKey(key)
        }
    }

    /** 获取 Explore 页面角色卡的收藏状态 */
    fun isExploreAgentFavorite(agentId: String): Boolean {
        if (agentId.isBlank()) return false
        return curUserSetting.decodeBool("$KEY_PREFIX_EXPLORE_FAVORITE$agentId", false)
    }

    /** 获取所有已收藏的 Explore 角色ID */
    fun getExploreFavoriteAgentIds(): List<String> {
        val keys = curUserSetting.allKeys() ?: return emptyList()
        return keys
            .asSequence()
            .filter { it.startsWith(KEY_PREFIX_EXPLORE_FAVORITE) }
            .mapNotNull { key ->
                val agentId = key.removePrefix(KEY_PREFIX_EXPLORE_FAVORITE)
                if (curUserSetting.decodeBool(key, false)) agentId else null
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
        curUserSetting.putBoolean("conversation_pinned_$agentId", pinned)
    }

    /** 获取会话置顶状态 */
    fun isConversationPinned(agentId: String): Boolean {
        return curUserSetting.decodeBool("conversation_pinned_$agentId", false)
    }

    /** 设置会话隐藏状态 */
    fun setConversationHidden(agentId: String, hidden: Boolean) {
        curUserSetting.putBoolean("conversation_hidden_$agentId", hidden)
        if (hidden) {
            // 记录隐藏时的时间戳，用于判断是否有新消息
            curUserSetting.putLong("conversation_hidden_time_$agentId", System.currentTimeMillis())
        } else {
            curUserSetting.removeValueForKey("conversation_hidden_time_$agentId")
        }
    }

    /** 获取会话隐藏状态 */
    fun isConversationHidden(agentId: String): Boolean {
        return curUserSetting.decodeBool("conversation_hidden_$agentId", false)
    }

    /** 获取会话隐藏时间（用于判断是否应该恢复显示） */
    fun getConversationHiddenTime(agentId: String): Long {
        return curUserSetting.decodeLong("conversation_hidden_time_$agentId", 0L)
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
