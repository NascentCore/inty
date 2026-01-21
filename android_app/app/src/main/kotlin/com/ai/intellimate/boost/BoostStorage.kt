/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.data.store.jsonDataStore
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first

private val Context.boostState by jsonDataStore("boost_state", BoostStateSnapshot())

/** Boost 状态本地存储管理类。 */
internal object BoostStorage {
    val boostState: Flow<BoostStateSnapshot>
        get() = Utils.getApp().boostState.data

    suspend fun update(transform: (BoostStateSnapshot) -> BoostStateSnapshot) {
        try {
            Utils.getApp().boostState.updateData(transform)
        } catch (e: Exception) {
            LogUtils.e("BoostStorage", "保存 Boost 状态失败: ${e.message}")
        }
    }

    /** 保存 Boost 状态快照 */
    suspend fun saveBoostState(snapshot: BoostStateSnapshot) {
        try {
            Utils.getApp().boostState.updateData { snapshot }
        } catch (e: Exception) {
            LogUtils.e("BoostStorage", "保存 Boost 状态失败: ${e.message}")
        }
    }

    /** 获取 Boost 状态快照 */
    suspend fun getBoostState(): BoostStateSnapshot {
        return boostState.first()
    }
}
