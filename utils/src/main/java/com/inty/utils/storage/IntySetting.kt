package com.inty.utils.storage

import com.inty.utils.AppEnv
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

        last.close()
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
        return getCurUserID().isNotEmpty()
    }

    fun login(isGuest: Boolean, uid: String, token: String) {
        changeUser(uid)
        setToken(token)
        if (isGuest) {
            allUserSetting.putString("guest_uid", uid)
        }
    }

}