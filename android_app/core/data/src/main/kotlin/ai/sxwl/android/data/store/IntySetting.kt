package ai.sxwl.android.data.store

import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.os.Handler
import android.os.Looper
import com.tencent.mmkv.MMKV
import kotlin.random.Random

object IntySetting {

    // App级通用标记的存储 使用的对象
    private val allUserSetting: MMKV

    // 当前用户级别的数据存储
    private var curUserSetting: MMKV

    // 当前UserId
    private var curUid: String = ""

    init {
        MMKV.initialize(Utils.getApp())
        allUserSetting = MMKV.defaultMMKV(MMKV.SINGLE_PROCESS_MODE, AppUtils.getPackageName())

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

        // 然后更新token
        changeUser(uid)
        setToken(token)

        // 再次清除缓存，确保使用新token创建客户端
        // 虽然getClient()会清除旧token的缓存，但这里双重保险
        IntyNetworkManager.clearClientCache()
    }

    /** 用于业务标记消息已读的最后一条消息的判断 */
    fun isConversationReaded(agentID: String, lastMessage: String): Boolean {
        val configLastMsg = curUserSetting.decodeString("conversation_last_$agentID", agentID)
        LogUtils.d("$agentID = $configLastMsg, new=$lastMessage")
        return (configLastMsg == lastMessage)
    }

    /** 用于业务标记消息已读的最后一条消息 */
    fun setConversationReaded(agentID: String, lastMessage: String) {
        LogUtils.d("$agentID = $lastMessage")
        curUserSetting.putString("conversation_last_$agentID", lastMessage)
    }

    /** 记录是否显示keepTalking按钮（全局设置） */
    fun setShowKeepTalking(show: Boolean) {
        curUserSetting.putBoolean("show_keep_talking", show)
    }

    fun isShowKeepTalking(): Boolean {
        return curUserSetting.decodeBool("show_keep_talking", false)
    }

    /** 自动播放语音消息（全局设置，默认开启） */
    fun setAutoPlayAudio(play: Boolean) {
        curUserSetting.putBoolean("auto_play_audio", play)
    }

    fun isAutoPlayAudio(): Boolean {
        // 默认值为true（开启）
        return curUserSetting.decodeBool("auto_play_audio", true)
    }

    // region Premium model相关设置

    // endregion

    // 标记是否已经提示过订阅过期的弹窗
    fun hasTipsVipExpired(): Boolean {
        return curUserSetting.getBoolean("has_tips_vip_expired", false)
    }

    fun setTipsVipExpired(showed: Boolean) {
        curUserSetting.putBoolean("has_tips_vip_expired", showed)
    }

    // 标记是否已经有可用的App更新，用于红点标记
    fun hasAppUpdateTips(): Boolean {
        return curUserSetting.getBoolean("has_app_update_tips", false)
    }

    fun setAppUpdateTips(showed: Boolean) {
        curUserSetting.putBoolean("has_app_update_tips", showed)
    }

    fun appGooglePlayUrl(): String {
        return curUserSetting.getString("app_google_play_url", "") ?: ""
    }

    fun setAppGooglePlayUrl(url: String) {
        curUserSetting.putString("app_google_play_url", url)
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

    /** 保存指定agent的聊天数据 使用简单的字符串存储，避免复杂的JSON序列化 */
    fun saveChatMessages(agentId: String, messages: List<ai.sxwl.android.data.api.model.MsgInfo>) {
        try {
            // 暂时禁用数据持久化，避免序列化问题
            // TODO: 实现更简单的数据存储方案
            LogUtils.d(
                "Chat messages persistence temporarily disabled for agent $agentId (${messages.size} messages)"
            )
        } catch (e: Exception) {
            LogUtils.e("Failed to save chat messages for agent $agentId: ${e.message}")
        }
    }

    /** 获取指定agent的聊天数据 暂时返回空列表，避免反序列化问题 */
    fun getChatMessages(agentId: String): List<ai.sxwl.android.data.api.model.MsgInfo> {
        // 暂时禁用数据持久化，避免反序列化问题
        // TODO: 实现更简单的数据存储方案
        LogUtils.d("Chat messages loading temporarily disabled for agent $agentId")
        return emptyList()
    }

    /** 保存指定agent的分页状态 */
    fun saveChatPaginationState(
        agentId: String,
        offset: Int,
        hasMore: Boolean,
        isInitialLoaded: Boolean,
    ) {
        curUserSetting.putInt("chat_offset_$agentId", offset)
        curUserSetting.putBoolean("chat_has_more_$agentId", hasMore)
        curUserSetting.putBoolean("chat_initial_loaded_$agentId", isInitialLoaded)
        LogUtils.d(
            "Saved pagination state for agent $agentId: offset=$offset, hasMore=$hasMore, initialLoaded=$isInitialLoaded"
        )
    }

    /** 获取指定agent的分页状态 */
    fun getChatPaginationState(agentId: String): Triple<Int, Boolean, Boolean> {
        val offset = curUserSetting.decodeInt("chat_offset_$agentId", 0)
        val hasMore = curUserSetting.decodeBool("chat_has_more_$agentId", true)
        val isInitialLoaded = curUserSetting.decodeBool("chat_initial_loaded_$agentId", false)
        return Triple(offset, hasMore, isInitialLoaded)
    }

    /** 清除指定agent的聊天数据 */
    fun clearChatData(agentId: String) {
        curUserSetting.removeValueForKey("chat_messages_$agentId")
        curUserSetting.removeValueForKey("chat_offset_$agentId")
        curUserSetting.removeValueForKey("chat_has_more_$agentId")
        curUserSetting.removeValueForKey("chat_initial_loaded_$agentId")
        LogUtils.d("Cleared chat data for agent $agentId")
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
        LogUtils.d("Cleared all chat data")
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
