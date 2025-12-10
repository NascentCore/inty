/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.utils.MoshiUtils
import com.tencent.mmkv.MMKV

/** Boost 状态本地存储管理类，使用 MMKV 持久化。 */
internal object BoostStorage {

    private val mmkv: MMKV by lazy {
        // MKKV.initialize(app) 在 IntelliMateApp.onCreate() 中调用
        MMKV.mmkvWithID("boost_state", MMKV.MULTI_PROCESS_MODE)
    }
    private const val KEY_BOOST_STATE = "boost_state_snapshot"

    /** 保存 Boost 状态快照 */
    fun saveBoostState(snapshot: BoostStateSnapshot) {
        try {
            val json = MoshiUtils.toJson(snapshot)
            mmkv.putString(KEY_BOOST_STATE, json)
        } catch (e: Exception) {
            LogUtils.e("BoostStorage", "保存 Boost 状态失败: ${e.message}")
        }
    }

    /** 获取 Boost 状态快照 */
    fun getBoostState(): BoostStateSnapshot {
        val json = mmkv.decodeString(KEY_BOOST_STATE)
        return if (json.isNullOrEmpty()) {
            BoostStateSnapshot()
        } else {
            try {
                MoshiUtils.fromJson<BoostStateSnapshot>(json) ?: BoostStateSnapshot()
            } catch (e: Exception) {
                LogUtils.e("BoostStorage", "解析 Boost 状态失败: ${e.message}")
                // 如果解析失败，清除损坏的缓存数据
                try {
                    mmkv.removeValueForKey(KEY_BOOST_STATE)
                } catch (clearException: Exception) {
                    LogUtils.e("BoostStorage", "清除损坏数据失败: ${clearException.message}")
                }
                BoostStateSnapshot()
            }
        }
    }
}
