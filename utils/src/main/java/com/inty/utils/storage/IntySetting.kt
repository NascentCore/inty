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

    fun isGuestUser(): Boolean {
        return getCurUserID() == geGuestUserID()
    }

    fun changeUser(uid: String) {
        val last = curUserSetting

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
    
    // 标记用户主动发起的对话
    fun setUserInitiatedConversation(agentID: String) {
        curUserSetting.putBoolean("user_initiated_$agentID", true)
    }
    
    // 检查对话是否为用户主动发起
    fun isUserInitiatedConversation(agentID: String): Boolean {
        return curUserSetting.decodeBool("user_initiated_$agentID", false)
    }

    fun setShowKeepTalking(show: Boolean) {
        curUserSetting.putBoolean("show_keep_talking", show)
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

    // 角色专用的keep talking设置 (三状态: true/false/null)
    fun setAgentKeepTalking(agentId: String, show: Boolean?) {
        if (show == null) {
            curUserSetting.removeValueForKey("agent_keep_talking_$agentId")
        } else {
            curUserSetting.putBoolean("agent_keep_talking_$agentId", show)
        }
    }

    fun getAgentKeepTalking(agentId: String): Boolean? {
        return if (curUserSetting.containsKey("agent_keep_talking_$agentId")) {
            curUserSetting.decodeBool("agent_keep_talking_$agentId", false)
        } else {
            null // 默认状态：跟随全局配置
        }
    }

    // 获取最终的keep talking显示状态（角色设置优先于全局设置）
    fun shouldShowKeepTalking(agentId: String): Boolean {
        val agentSetting = getAgentKeepTalking(agentId)
        return agentSetting ?: isShowKeepTalking()
    }

    fun logout() {
        setToken("")
        if (isGuestUser()) {
            return
        }
        changeUser(geGuestUserID())
    }

    // 通用的用户信息存储方法（不依赖具体的 UserProfile 类）
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

}