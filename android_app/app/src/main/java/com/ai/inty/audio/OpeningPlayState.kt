package com.ai.inty.audio

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/**
 *                    .::::.
 *                  .::::::::.
 *                 :::::::::::      HeartMate App
 *             ..:::::::::::'
 *           '::::::::::::'
 *             .::::::::::
 *        '::::::::::::::..
 *             ..::::::::::::.
 *           ``::::::::::::::::
 *            ::::``:::::::::'        .:::.
 *           ::::'   ':::::'       .::::::::.
 *         .::::'      ::::     .:::::::'::::.
 *        .:::'       :::::  .:::::::::' ':::::.
 *       .::'        :::::.:::::::::'      ':::::.
 *      .::'         ::::::::::::::'         ``::::.
 *  ...:::           ::::::::::::'              ``::.
 * ```` ':.          ':::::::::'                  ::::..
 *                    '.:::::'                    ':'````..
 *
 * You may think you know what the following code does.
 * But you don't. Trust me.
 * Fiddle with it, and you'll spend many a sleepless
 * night cursing the moment you thought you'd be clever
 * enough to "optimize" the code below.
 * Now close this file and go play with something else.
 *
 *                     ---Created by HeartMate on 2025/9/10.
 */
object OpeningPlayState {
    private val playedMap = mutableMapOf<String, Boolean>()

    // 使用 Mutex 确保线程安全
    private val mutex = Mutex()

    private val coroutineScope = CoroutineScope(Job() + Dispatchers.Default)

    /** 查看本agent的开场白，在App本次启用运行期间，是否播放过 线程安全的同步方法 */
    fun agentOpeningPlayed(agentId: String): Boolean {
        return playedMap.getOrDefault(agentId, false)
    }

    /** 标记指定agent的开场白已播放 线程安全的协程方法 */
    suspend fun openingPlayed(agentId: String) {
        withContext(Dispatchers.Default) { mutex.withLock { playedMap[agentId] = true } }
    }

    /** 异步标记指定agent的开场白已播放 不阻塞调用线程的版本 */
    fun openingPlayedAsync(agentId: String) {
        coroutineScope.launch { openingPlayed(agentId) }
    }

    /** 清除所有播放记录 线程安全的协程方法 */
    suspend fun clearAllPlayed() {
        withContext(Dispatchers.Default) { mutex.withLock { playedMap.clear() } }
    }

    /** 清除指定agent的播放记录 线程安全的协程方法 */
    suspend fun clearAgentPlayed(agentId: String) {
        withContext(Dispatchers.Default) { mutex.withLock { playedMap.remove(agentId) } }
    }
}
