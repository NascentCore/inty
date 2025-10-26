package com.ai.intellimate.audio

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

object OpeningPlayState {
    private val playedMap = mutableMapOf<String, Boolean>()
// 使用Mutex保证线程安全
    private val mutex = Mutex()

    private val coroutineScope = CoroutineScope(Job() + Dispatchers.Default)

    /** 查看本agent的开场白色，在App本次启用运行期间，是否通过线程安全的同步方法进行播放 */
    fun agentOpeningPlayed(agentId: String): Boolean {
        return playedMap.getOrDefault(agentId, false)
    }

    /** 标记指定代理的开放场白色已播放线程安全的协程方法 */
    suspend fun openingPlayed(agentId: String) {
        withContext(Dispatchers.Default) { mutex.withLock { playedMap[agentId] = true } }
    }

    /** 异步标记指定代理的开场白已播放不阻塞调用线程的版本 */
    fun openingPlayedAsync(agentId: String) {
        coroutineScope.launch { openingPlayed(agentId) }
    }

    /** 清除所有播放记录线程安全的协程方法 */
    suspend fun clearAllPlayed() {
        withContext(Dispatchers.Default) { mutex.withLock { playedMap.clear() } }
    }

    /** 清除指定代理的播放记录线程安全的协程方法 */
    suspend fun clearAgentPlayed(agentId: String) {
        withContext(Dispatchers.Default) { mutex.withLock { playedMap.remove(agentId) } }
    }
}
