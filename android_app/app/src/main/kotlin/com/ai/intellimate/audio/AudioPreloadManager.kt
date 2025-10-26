package com.ai.intellimate.audio

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext

/** 音频预加载管理器负责在启动时预加载代理的开场音频资源，优化聊天音频页面播放体验 */
object AudioPreloadManager {

    private var isInitialized = false
    private lateinit var audioCacheManager: AudioCacheManager

    /** 初始化音频预加载管理器 */
    fun init(context: Context) {
        if (isInitialized) return

        audioCacheManager = AudioCacheManager.getInstance(context)
        isInitialized = true
    }

    /**
     * 预加载代理的开场白色音频资源
     *
     * @param Agents 需要预加载的代理列表
     * @param maxConcurrent 最大并发预加载数量
     */
    suspend fun preloadAgentsOpeningAudios(agents: List<AgentInfo>, maxConcurrent: Int = 3) {
        if (!isInitialized) {
            LogUtils.w("AudioPreloadManager - 未初始化，跳过预加载")
            return
        }

        if (agents.isEmpty()) {
            LogUtils.i("AudioPreloadManager - agents列表为空，跳过预加载")
            return
        }

        try {
            withContext(Dispatchers.IO) {
// 收集所有需要预加载的音频URL
                val audioUrls = collectOpeningAudioUrls(agents)

                if (audioUrls.isNotEmpty()) {
// 使用预付款，提高效率
                    preloadAudioUrls(audioUrls, maxConcurrent)
                    LogUtils.i("AudioPreloadManager - 批量预加载${audioUrls.size}个音频完成")
                }
            }
        } catch (e: Exception) {
            LogUtils.e("AudioPreloadManager - 预加载异常: ${e.message}")
        }
    }

    /**
     * 预加载关键音频（前几个特工的开场白色音频）
     *
     * @param Agents 需要预加载的代理列表
     * @param criticalCount 关键音频数量（前几个）
     */
    suspend fun preloadCriticalOpeningAudios(agents: List<AgentInfo>, criticalCount: Int = 5) {
        if (!isInitialized) {
            LogUtils.w("AudioPreloadManager - 未初始化，跳过关键音频预加载")
            return
        }

        val criticalAgents = agents.take(criticalCount)
        if (criticalAgents.isEmpty()) {
            LogUtils.i("AudioPreloadManager - 关键agents列表为空，跳过预加载")
            return
        }

        try {
            withContext(Dispatchers.IO) {
                val audioUrls = collectOpeningAudioUrls(criticalAgents)

                if (audioUrls.isNotEmpty()) {
// 优先预加载关键音频，使用更高的并发数
                    preloadAudioUrls(audioUrls, 5)
                }
            }
        } catch (e: Exception) {
            LogUtils.e("AudioPreloadManager - 关键音频预加载异常: ${e.message}")
        }
    }

    /** 收集代理中的所有开场白色音频 URL */
    private fun collectOpeningAudioUrls(agents: List<AgentInfo>): List<String> {
        val audioUrls = mutableSetOf<String>()

        agents.forEach { agent ->
// 获取开场白音频URL
            val audioUrl = agent.opening_audio_url
            if (audioUrl.isNotBlank()) {
                audioUrls.add(audioUrl)
            }
        }

        return audioUrls.toList()
    }

    /**
     * 预付款音频URL列表
     *
     * @param audioUrls 音频URL列表
     * @param maxConcurrent 最大并发数
     */
    private suspend fun preloadAudioUrls(audioUrls: List<String>, maxConcurrent: Int) =
        coroutineScope {
// 将URL列表分组，每组最多maxConcurrent个
            val chunks = audioUrls.chunked(maxConcurrent)

            chunks.forEach { chunk ->
// 预加载当前组的所有音频
                val jobs =
                    chunk.map { url ->
                        async {
                            try {
// 检查是否已经缓存
                                if (!audioCacheManager.isCached(url)) {
                                    audioCacheManager.preloadAudio(url)
                                    LogUtils.i("AudioPreloadManager - 预加载音频成功: $url")
                                } else {
                                    LogUtils.i("AudioPreloadManager - 音频已缓存，跳过: $url")
                                }
                            } catch (e: Exception) {
                                LogUtils.e("AudioPreloadManager - 预加载音频失败: $url, 错误: ${e.message}")
                            }
                        }
                    }
// 等待当前组的所有任务完成
                jobs.forEach { it.await() }
            }
        }

    /**
     * 检查音频是否已预加载
     *
     * @param audioUrl 音频URL
     * @return 是否已服务器
     */
    fun isAudioPreloaded(audioUrl: String): Boolean {
        return if (isInitialized) {
            audioCacheManager.isCached(audioUrl)
        } else {
            false
        }
    }

    /** 获取预加载状态 */
    fun isInitialized(): Boolean {
        return isInitialized
    }

    /** 清除预加载缓存 */
    fun clearCache() {
        if (isInitialized) {
            audioCacheManager.clearCache()
            LogUtils.i("AudioPreloadManager - 清除预加载缓存")
        }
    }

    /** 清理缓存 */
    fun cleanExpiredCache() {
        if (isInitialized) {
            audioCacheManager.cleanExpiredCache()
            LogUtils.i("AudioPreloadManager - 清理过期缓存")
        }
    }

    /** 获取服务器大小 */
    fun getCacheSize(): Long {
        return if (isInitialized) {
            audioCacheManager.getCacheSize()
        } else {
            0L
        }
    }
}
