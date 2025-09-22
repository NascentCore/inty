package com.inty.utils.storage

import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.tencent.mmkv.MMKV


object IntySetting {

    private val allUserSetting: MMKV

    private var curUserSetting: MMKV

    private var curUid: String = ""

    init {
        MMKV.initialize(AppEnv.context)
        allUserSetting = MMKV.defaultMMKV(MMKV.SINGLE_PROCESS_MODE, AppEnv.APPLICATION_ID)

        curUid = getCurUserID()
        curUserSetting = MMKV.mmkvWithID("user_$curUid", MMKV.MULTI_PROCESS_MODE)
    }

    fun getCurUserID(): String {
        return allUserSetting.decodeString("cur_uid") ?: ""
    }

    private fun geGuestUserID(): String {
        return allUserSetting.decodeString("guest_uid") ?: ""
    }

    /**
     * 判断当前用户是否是 游客
     */
    fun isGuestUser(): Boolean {
        return getCurUserID() == geGuestUserID()
    }

    /**
     * 判断是否有年龄，当前业务逻辑，>18岁的选择，age_group就不会null，<18岁，无法进行选择交互，也不会存储到服务端
     */
    private fun userAgeYoung(): Boolean {
        val ageGroup = getUserProfileData("age_group")
        return ageGroup == null || ageGroup.trim() == "<18"
    }

    /**
     * 游客状态，且年龄未设置（<18岁也不让设置，所以设置必然>18岁），则不能使用聊天
     */
    fun needBlockInput(): Boolean {
        return isGuestUser() && userAgeYoung()
    }

    fun changeUser(uid: String) {
        curUserSetting

        curUid = uid
        curUserSetting = MMKV.mmkvWithID("user_$curUid", MMKV.MULTI_PROCESS_MODE)
        allUserSetting.putString("cur_uid", uid)

//        last.close()
    }

    fun setToken(token: String) {
        curUserSetting.putString("token", token)
    }

    fun getCurToken(): String {
        return curUserSetting.decodeString("token") ?: ""
    }

    fun setDeviceID(id: String?) {
        allUserSetting.putString("deviceID", id)
    }

    fun getDeviceID(): String? {
        return allUserSetting.decodeString("deviceID")
    }

    fun isLogin(): Boolean {
        return getCurUserID().isNotEmpty() && getCurToken().isNotEmpty()
    }

    fun login(isGuest: Boolean, uid: String, token: String) {
        changeUser(uid)
        setToken(token)
        if (isGuest) {
            allUserSetting.putString("guest_uid", uid)
        }
    }

    fun isConversationReaded(agentID: String, lastMessage: String): Boolean {
        val configLastMsg = curUserSetting.decodeString("conversation_last_$agentID", agentID)
        EasyLog.log("$agentID = $configLastMsg, new=$lastMessage")
        return (configLastMsg == lastMessage)
    }

    fun setConversationReaded(agentID: String, lastMessage: String) {
        EasyLog.log("$agentID = $lastMessage")
        curUserSetting.putString("conversation_last_$agentID", lastMessage)
    }


    fun setShowKeepTalking(show: Boolean) {
        curUserSetting.putBoolean("show_keep_talking", show)
        // 当全局设置改变时，重置所有角色的keep talking设置为与全局一致
        resetAllAgentKeepTalkingToGlobal(show)
    }

    fun isShowKeepTalking(): Boolean {
        return curUserSetting.decodeBool("show_keep_talking", false)
    }

    fun setAutoPlayAudio(play: Boolean) {
        curUserSetting.putBoolean("auto_play_audio", play)
    }

    fun isAutoPlayAudio(): Boolean {
        return curUserSetting.decodeBool("auto_play_audio", false)
    }

    // 角色专用的keep talking设置 (二状态: true/false)
    fun setAgentKeepTalking(agentId: String, show: Boolean) {
        curUserSetting.putBoolean("agent_keep_talking_$agentId", show)
    }

    fun getAgentKeepTalking(agentId: String): Boolean? {
        return if (curUserSetting.containsKey("agent_keep_talking_$agentId")) {
            curUserSetting.decodeBool("agent_keep_talking_$agentId", false)
        } else {
            null // 没有专门设置时返回null，使用全局设置
        }
    }

    // 获取最终的keep talking显示状态（有专门设置时使用专门设置，否则使用全局设置）
    fun shouldShowKeepTalking(agentId: String): Boolean {
        val agentSetting = getAgentKeepTalking(agentId)
        return agentSetting ?: isShowKeepTalking()
    }

    // 重置所有角色的keep talking设置为与全局设置一致
    private fun resetAllAgentKeepTalkingToGlobal(globalSetting: Boolean) {
        // 获取所有以"agent_keep_talking_"开头的key
        val allKeys = curUserSetting.allKeys()
        allKeys?.forEach { key ->
            if (key.startsWith("agent_keep_talking_")) {
                curUserSetting.putBoolean(key, globalSetting)
            }
        }
    }

    //region Premium model相关设置

    /**
     * 设置全局app的模型，都使用高级vip模型
     */
    fun setShowPremiumModel(show: Boolean) {
        curUserSetting.putBoolean("show_premium_model", show)
        // 当全局设置改变时，重置所有角色的premium model设置为与全局一致
        resetAllAgentPremiumModelToGlobal(show)
    }

    /**
     * 判断是否使用全局 高级vip模型
     */
    fun isShowPremiumModel(): Boolean {
        return curUserSetting.decodeBool("show_premium_model", false)
    }

    // 角色专用的premium model设置 (二状态: true/false)
    fun setAgentPremiumModel(agentId: String, show: Boolean) {
        curUserSetting.putBoolean("agent_premium_model_$agentId", show)
    }

    fun getAgentPremiumModel(agentId: String): Boolean? {
        return if (curUserSetting.containsKey("agent_premium_model_$agentId")) {
            curUserSetting.decodeBool("agent_premium_model_$agentId", false)
        } else {
            null // 没有专门设置时返回null，使用全局设置
        }
    }

    // 获取最终的premium model显示状态（有专门设置时使用专门设置，否则使用全局设置）
    fun shouldShowPremiumModel(agentId: String): Boolean {
        val agentSetting = getAgentPremiumModel(agentId)
        return agentSetting ?: isShowPremiumModel()
    }

    // 重置所有角色的premium model设置为与全局设置一致
    private fun resetAllAgentPremiumModelToGlobal(globalSetting: Boolean) {
        // 获取所有以"agent_premium_model_"开头的key
        val allKeys = curUserSetting.allKeys()
        allKeys?.forEach { key ->
            if (key.startsWith("agent_premium_model_")) {
                curUserSetting.putBoolean(key, globalSetting)
            }
        }
    }
    //endregion

    //标记是否已经提示过订阅过期的弹窗
    fun hasTipsVipExpired(): Boolean {
        return curUserSetting.getBoolean("has_tips_vip_expired", false)
    }

    fun setTipsVipExpired(showed: Boolean) {
        curUserSetting.putBoolean("has_tips_vip_expired", showed)
    }

    //标记是否已经有可用的App更新，用于红点标记
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
        if (isGuestUser()) {
            isLoggingOut = false
            return
        }
        changeUser(geGuestUserID())
        // 延迟重置标志，确保401处理器有时间识别
        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            isLoggingOut = false
        }, 2000)
    }

    fun isLoggingOut(): Boolean {
        return isLoggingOut
    }


    //用于推荐接口后端sort随机排序的seed种子
    fun sortSeed(): Int {
        return curUserSetting.getInt("current_sort_seed", 0)
    }

    fun updateSortSeed(seed: Int) {
        curUserSetting.putInt("current_sort_seed", seed)
    }


    //region 通用的用户信息存储方法（不依赖具体的 UserProfile 类）
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
    //endregion


}
