package ai.sxwl.android.data.store

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.util.concurrent.ConcurrentHashMap

/**
 * 用户绑定DataStore管理器
 * 实现所有存储数据与用户绑定，切换用户会切换存储文件的空间
 *
 * 设计原则：
 * 1. 每个用户有独立的存储空间
 * 2. Guest用户和正式用户数据完全隔离
 * 3. 用户切换时自动切换存储空间
 * 4. 支持数据迁移和清理
 */
class UserBoundDataStore private constructor(context: Context) {

    private val appContext = context.applicationContext
    private var currentUserId: String = ""

    companion object {
        private const val GUEST_USER_ID = "guest"
        private const val DATASTORE_SUFFIX = "_preferences"

        @Volatile
        private var INSTANCE: UserBoundDataStore? = null

        fun getInstance(context: Context): UserBoundDataStore {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: UserBoundDataStore(context).also { INSTANCE = it }
            }
        }
    }

    /**
     * 设置当前用户ID，切换存储空间
     */
    fun setCurrentUserId(userId: String) {
        currentUserId = userId
    }

    /**
     * 获取当前用户ID
     */
    fun getCurrentUserId(): String = currentUserId

    /**
     * 获取用户绑定的DataStore名称
     */
    private fun getUserDataStoreName(userId: String): String {
        return "${userId}${DATASTORE_SUFFIX}"
    }

    // 缓存不同用户的DataStore实例
    private val userDataStores = ConcurrentHashMap<String, DataStore<Preferences>>()

    /**
     * 获取或创建指定名称的DataStore
     */
    private fun getOrCreateDataStore(name: String): DataStore<Preferences> {
        return userDataStores.getOrPut(name) {
            PreferenceDataStoreFactory.create(
                produceFile = { appContext.preferencesDataStoreFile(name) }
            )
        }
    }

    /**
     * 获取当前用户的DataStore
     */
    private fun getCurrentUserDataStore(): DataStore<Preferences> {
        val dataStoreName = getUserDataStoreName(currentUserId)
        return getOrCreateDataStore(dataStoreName)
    }

    /**
     * 获取指定用户的DataStore
     */
    private fun getUserDataStore(userId: String): DataStore<Preferences> {
        val dataStoreName = getUserDataStoreName(userId)
        return getOrCreateDataStore(dataStoreName)
    }

    //region 用户相关数据存储

    /**
     * 保存用户Token
     */
    suspend fun saveUserToken(token: String) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.User.CURRENT_USER_TOKEN] = token
        }
    }

    /**
     * 获取用户Token
     */
    fun getUserToken(): Flow<String?> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.User.CURRENT_USER_TOKEN]
        }
    }

    /**
     * 保存用户信息
     */
    suspend fun saveUserInfo(userInfo: String) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.User.CURRENT_USER_INFO] = userInfo
        }
    }

    /**
     * 获取用户信息
     */
    fun getUserInfo(): Flow<String?> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.User.CURRENT_USER_INFO]
        }
    }

    /**
     * 保存是否为Guest用户
     */
    suspend fun saveIsGuest(isGuest: Boolean) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.User.IS_GUEST] = isGuest
        }
    }

    /**
     * 获取是否为Guest用户
     */
    fun getIsGuest(): Flow<Boolean> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.User.IS_GUEST] ?: true
        }
    }

    /**
     * 保存VIP状态
     */
    suspend fun saveIsVip(isVip: Boolean) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.User.IS_VIP] = isVip
        }
    }

    /**
     * 获取VIP状态
     */
    fun getIsVip(): Flow<Boolean> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.User.IS_VIP] ?: false
        }
    }

    /**
     * 保存VIP过期时间
     */
    suspend fun saveVipExpireTime(expireTime: Long) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.User.VIP_EXPIRE_TIME] = expireTime
        }
    }

    /**
     * 获取VIP过期时间
     */
    fun getVipExpireTime(): Flow<Long> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.User.VIP_EXPIRE_TIME] ?: 0L
        }
    }

    /**
     * 保存最后登录时间
     */
    suspend fun saveLastLoginTime(loginTime: Long) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.User.LAST_LOGIN_TIME] = loginTime
        }
    }

    /**
     * 获取最后登录时间
     */
    fun getLastLoginTime(): Flow<Long> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.User.LAST_LOGIN_TIME] ?: 0L
        }
    }

    //endregion

    //region 应用设置数据存储

    /**
     * 保存Show Keep Talking按钮设置
     */
    suspend fun saveShowKeepTalkingButton(show: Boolean) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.App.SHOW_KEEP_TALKING_BUTTON] = show
        }
    }

    /**
     * 获取Show Keep Talking按钮设置
     */
    fun getShowKeepTalkingButton(): Flow<Boolean> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.App.SHOW_KEEP_TALKING_BUTTON] ?: false
        }
    }

    /**
     * 保存自动播放语音消息设置
     */
    suspend fun saveAutoPlayVoiceMessages(autoPlay: Boolean) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.App.AUTO_PLAY_VOICE_MESSAGES] = autoPlay
        }
    }

    /**
     * 获取自动播放语音消息设置
     */
    fun getAutoPlayVoiceMessages(): Flow<Boolean> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.App.AUTO_PLAY_VOICE_MESSAGES] ?: true
        }
    }

    //endregion

    //region 订阅相关数据存储

    /**
     * 保存订阅计划数据
     */
    suspend fun saveSubscriptionPlans(plansJson: String) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.Subscription.SUBSCRIPTION_PLANS] = plansJson
        }
    }

    /**
     * 获取订阅计划数据
     */
    fun getSubscriptionPlans(): Flow<String?> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.Subscription.SUBSCRIPTION_PLANS]
        }
    }

    /**
     * 保存当前订阅信息
     */
    suspend fun saveCurrentSubscription(subscriptionJson: String) {
        getCurrentUserDataStore().edit { preferences ->
            preferences[UserBoundDataStoreKeys.Subscription.CURRENT_SUBSCRIPTION] = subscriptionJson
        }
    }

    /**
     * 获取当前订阅信息
     */
    fun getCurrentSubscription(): Flow<String?> {
        return getCurrentUserDataStore().data.map { preferences ->
            preferences[UserBoundDataStoreKeys.Subscription.CURRENT_SUBSCRIPTION]
        }
    }

    //endregion

    //region 数据管理方法

    /**
     * 清除当前用户的所有数据
     */
    suspend fun clearCurrentUserData() {
        getCurrentUserDataStore().edit { preferences ->
            preferences.clear()
        }
    }

    /**
     * 清除指定用户的所有数据
     */
    suspend fun clearUserData(userId: String) {
        getUserDataStore(userId).edit { preferences ->
            preferences.clear()
        }
    }

    // 如需实现数据迁移，请针对具体键值做类型安全的拷贝，避免Any类型写入造成编译错误

    /**
     * 获取所有用户ID列表
     */
    fun getAllUserIds(): List<String> {
        // 这里需要实现获取所有用户ID的逻辑
        // 可以通过扫描DataStore文件来实现
        return listOf(GUEST_USER_ID)
    }

    //endregion
}

/**
 * 扩展DataStoreKeys，添加新的键值定义
 */
object UserBoundDataStoreKeys {
    object User {
        val CURRENT_USER_TOKEN =
            stringPreferencesKey("current_user_token")
        val CURRENT_USER_INFO =
            stringPreferencesKey("current_user_info")
        val IS_GUEST = booleanPreferencesKey("is_guest")
        val IS_VIP = booleanPreferencesKey("is_vip")
        val VIP_EXPIRE_TIME =
            longPreferencesKey("vip_expire_time")
        val LAST_LOGIN_TIME =
            longPreferencesKey("last_login_time")
    }

    object App {
        val SHOW_KEEP_TALKING_BUTTON =
            booleanPreferencesKey("show_keep_talking_button")
        val AUTO_PLAY_VOICE_MESSAGES =
            booleanPreferencesKey("auto_play_voice_messages")
    }

    object Subscription {
        val SUBSCRIPTION_PLANS =
            stringPreferencesKey("subscription_plans")
        val CURRENT_SUBSCRIPTION =
            stringPreferencesKey("current_subscription")
    }
}
