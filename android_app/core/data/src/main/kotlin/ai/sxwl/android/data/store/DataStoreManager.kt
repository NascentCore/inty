package ai.sxwl.android.data.store

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/**
 * DataStore管理器
 * 提供键值对存储功能，按业务分组
 *
 * 特点：
 * - 按业务模块分组存储
 * - 提供统一的清理接口
 * - 使用Application Context避免内存泄漏
 */
class DataStoreManager internal constructor(context: Context) {

    private val appContext = context.applicationContext

    companion object {
        private const val USER_PREFERENCES_NAME = "user_preferences"
        private const val APP_PREFERENCES_NAME = "app_preferences"
        private const val DEVICE_PREFERENCES_NAME = "device_preferences"
        private const val CHAT_PREFERENCES_NAME = "chat_preferences"
        private const val AI_PREFERENCES_NAME = "ai_preferences"
    }

    // DataStore扩展属性
    private val Context.userDataStore: DataStore<Preferences> by preferencesDataStore(name = USER_PREFERENCES_NAME)
    private val Context.appDataStore: DataStore<Preferences> by preferencesDataStore(name = APP_PREFERENCES_NAME)
    private val Context.deviceDataStore: DataStore<Preferences> by preferencesDataStore(name = DEVICE_PREFERENCES_NAME)
    private val Context.chatDataStore: DataStore<Preferences> by preferencesDataStore(name = CHAT_PREFERENCES_NAME)
    private val Context.aiDataStore: DataStore<Preferences> by preferencesDataStore(name = AI_PREFERENCES_NAME)


    //用户相关方法

    suspend fun saveCurrentUserId(userId: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.CURRENT_USER_ID] = userId
        }
    }

    fun getCurrentUserId(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.CURRENT_USER_ID]
        }
    }

    suspend fun saveCurrentUserToken(token: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.CURRENT_USER_TOKEN] = token
        }
    }

    fun getCurrentUserToken(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.CURRENT_USER_TOKEN]
        }
    }

    suspend fun saveCurrentUserInfo(userInfo: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.CURRENT_USER_INFO] = userInfo
        }
    }

    fun getCurrentUserInfo(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.CURRENT_USER_INFO]
        }
    }


    suspend fun saveIsGuest(isGuest: Boolean) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.IS_GUEST] = isGuest
        }
    }

    fun getIsGuest(): Flow<Boolean> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.IS_GUEST] ?: true
        }
    }


    //region Guest的id，token，info
    suspend fun saveGuestId(guestId: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.GUEST_ID] = guestId
        }
    }

    fun getGuestId(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.GUEST_ID]
        }
    }

    suspend fun saveGuestToken(token: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.GUEST_TOKEN] = token
        }
    }

    fun getGuestToken(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.GUEST_TOKEN]
        }
    }

    suspend fun saveGuestUserInfo(guestInfoJson: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.GUEST_USER_INFO_JSON] = guestInfoJson
        }
    }

    fun getGuestUserInfo(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.GUEST_USER_INFO_JSON]
        }
    }
    //endregion

    //region user 相关的数据存储

    suspend fun saveUserId(userId: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.USER_ID] = userId
        }
    }

    fun getUserId(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.USER_ID]
        }
    }

    suspend fun saveUserToken(token: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.USER_TOKEN] = token
        }
    }

    fun getUserToken(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.USER_TOKEN]
        }
    }


    suspend fun saveUserInfo(userInfoJson: String) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.USER_INFO_JSON] = userInfoJson
        }
    }

    fun getUserInfo(): Flow<String?> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.USER_INFO_JSON]
        }
    }


    suspend fun saveIsVip(isVip: Boolean) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.IS_VIP] = isVip
        }
    }

    fun getIsVip(): Flow<Boolean> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.IS_VIP] ?: false
        }
    }

    suspend fun saveVipExpireTime(expireTime: Long) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.VIP_EXPIRE_TIME] = expireTime
        }
    }

    fun getVipExpireTime(): Flow<Long> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.VIP_EXPIRE_TIME] ?: 0L
        }
    }

    suspend fun saveLastLoginTime(loginTime: Long) {
        appContext.userDataStore.edit { preferences ->
            preferences[DataStoreKeys.User.LAST_LOGIN_TIME] = loginTime
        }
    }

    fun getLastLoginTime(): Flow<Long> {
        return appContext.userDataStore.data.map { preferences ->
            preferences[DataStoreKeys.User.LAST_LOGIN_TIME] ?: 0L
        }
    }
    //endregion


    //region  设备相关方法

    suspend fun saveDeviceId(deviceId: String) {
        appContext.deviceDataStore.edit { preferences ->
            preferences[DataStoreKeys.Device.DEVICE_ID] = deviceId
        }
    }

    fun getDeviceId(): Flow<String?> {
        return appContext.deviceDataStore.data.map { preferences ->
            preferences[DataStoreKeys.Device.DEVICE_ID]
        }
    }

    suspend fun saveAndroidId(androidId: String) {
        appContext.deviceDataStore.edit { preferences ->
            preferences[DataStoreKeys.Device.ANDROID_ID] = androidId
        }
    }

    fun getAndroidId(): Flow<String?> {
        return appContext.deviceDataStore.data.map { preferences ->
            preferences[DataStoreKeys.Device.ANDROID_ID]
        }
    }

    //endregion


    //region 聊天相关方法

    //endregion


    //region AI相关方法

    //endregion


    //region  清理方法

    /**
     * 清除用户数据
     */
    suspend fun clearUserData() {
        appContext.userDataStore.edit { preferences ->
            preferences.clear()
        }
    }

    /**
     * 清除应用数据
     */
    suspend fun clearAppData() {
        appContext.appDataStore.edit { preferences ->
            preferences.clear()
        }
    }

    /**
     * 清除设备数据
     */
    suspend fun clearDeviceData() {
        appContext.deviceDataStore.edit { preferences ->
            preferences.clear()
        }
    }

    /**
     * 清除聊天数据
     */
    suspend fun clearChatData() {
        appContext.chatDataStore.edit { preferences ->
            preferences.clear()
        }
    }

    /**
     * 清除AI数据
     */
    suspend fun clearAiData() {
        appContext.aiDataStore.edit { preferences ->
            preferences.clear()
        }
    }

    /**
     * 清除所有数据
     */
    suspend fun clearAllData() {
        clearUserData()
        clearAppData()
        clearDeviceData()
        clearChatData()
        clearAiData()
    }

    //endregion
}
