/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.data.store.jsonDataStore
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.receiveAsFlow

private val Context.boostState by jsonDataStore("boost_state", BoostStateSnapshot())

/** Boost 状态本地存储管理类。 */
internal object BoostStorage {
    val boostState: Flow<BoostStateSnapshot>
        get() = Utils.getApp().boostState.data

    private val _pointChanged = Channel<Pair<Int, Int>>()
    val pointChanged = _pointChanged.receiveAsFlow()

    suspend fun update(transform: (BoostStateSnapshot) -> BoostStateSnapshot) {
        try {
            Utils.getApp().boostState.updateData { last ->
                transform(last).also { updated ->
                    _pointChanged.trySend(
                        updated.availablePoints - last.availablePoints to updated.availablePoints
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e("BoostStorage", "保存 Boost 状态失败: ${e.message}")
        }
    }

    /** 保存 Boost 状态快照 */
    suspend fun saveBoostState(snapshot: BoostStateSnapshot) {
        try {
            Utils.getApp().boostState.updateData { last ->
                snapshot.also { updated ->
                    _pointChanged.trySend(
                        updated.availablePoints - last.availablePoints to updated.availablePoints
                    )
                }
            }
        } catch (e: Exception) {
            LogUtils.e("BoostStorage", "保存 Boost 状态失败: ${e.message}")
        }
    }

    /** 获取 Boost 状态快照 */
    suspend fun getBoostState(): BoostStateSnapshot {
        return boostState.first()
    }
}
