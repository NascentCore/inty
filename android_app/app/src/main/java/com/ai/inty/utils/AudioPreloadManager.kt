package com.ai.inty.utils

import android.content.Context
import com.ai.inty.audio.AudioCacheManager
import com.ai.inty.beans.AgentInfo
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext

/**
 * 音频预加载管理器
 * 负责在启动时预加载agents的开场白音频资源，优化聊天页面音频播放体验
 */
object AudioPreloadManager {
    
    private var isInitialized = false
    private lateinit var audioCacheManager: AudioCacheManager
    
    /**
     * 初始化音频预加载管理器
     */
    fun init(context: Context) {
        if (isInitialized) return
        
        audioCacheManager = AudioCacheManager.getInstance(context)
        isInitialized = true
        EasyLog.log("AudioPreloadManager - 初始化完成")
    }
    
    /**
     * 预加载agents的开场白音频资源
     * @param agents 需要预加载的agents列表
     * @param maxConcurrent 最大并发预加载数量
     */
    suspend fun preloadAgentsOpeningAudios(
        agents: List<AgentInfo>,
        maxConcurrent: Int = 3
    ) {
        if (!isInitialized) {
            EasyLog.log("AudioPreloadManager - 未初始化，跳过预加载", EasyLog.WARN)
            return
        }
        
        if (agents.isEmpty()) {
            EasyLog.log("AudioPreloadManager - agents列表为空，跳过预加载")
            return
        }
        
        EasyLog.log("AudioPreloadManager - 开始预加载 ${agents.size} 个agents的开场白音频")
        
        try {
            withContext(Dispatchers.IO) {
                // 收集所有需要预加载的音频URL
                val audioUrls = collectOpeningAudioUrls(agents)
                EasyLog.log("AudioPreloadManager - 收集到 ${audioUrls.size} 个音频URL")
                
                if (audioUrls.isNotEmpty()) {
                    // 使用并发预加载，提高效率
                    preloadAudioUrls(audioUrls, maxConcurrent)
                    EasyLog.log("AudioPreloadManager - 批量预加载音频完成")
                }
            }
            
            EasyLog.log("AudioPreloadManager - 所有音频预加载完成")
            
        } catch (e: Exception) {
            EasyLog.log("AudioPreloadManager - 预加载异常: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 预加载关键音频（前几个agents的开场白音频）
     * @param agents 需要预加载的agents列表
     * @param criticalCount 关键音频数量（前几个）
     */
    suspend fun preloadCriticalOpeningAudios(
        agents: List<AgentInfo>,
        criticalCount: Int = 5
    ) {
        if (!isInitialized) {
            EasyLog.log("AudioPreloadManager - 未初始化，跳过关键音频预加载", EasyLog.WARN)
            return
        }
        
        val criticalAgents = agents.take(criticalCount)
        if (criticalAgents.isEmpty()) {
            EasyLog.log("AudioPreloadManager - 关键agents列表为空，跳过预加载")
            return
        }
        
        EasyLog.log("AudioPreloadManager - 开始预加载前 $criticalCount 个关键开场白音频")
        
        try {
            withContext(Dispatchers.IO) {
                val audioUrls = collectOpeningAudioUrls(criticalAgents)
                
                if (audioUrls.isNotEmpty()) {
                    // 优先预加载关键音频，使用更高的并发数
                    preloadAudioUrls(audioUrls, 5)
                    EasyLog.log("AudioPreloadManager - 关键音频批量预加载完成")
                }
            }
            
            EasyLog.log("AudioPreloadManager - 关键音频预加载完成")
            
        } catch (e: Exception) {
            EasyLog.log("AudioPreloadManager - 关键音频预加载异常: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 收集agents中的所有开场白音频URL
     */
    private fun collectOpeningAudioUrls(agents: List<AgentInfo>): List<String> {
        val audioUrls = mutableSetOf<String>()
        
        agents.forEach { agent ->
            // 获取开场白音频URL
            val audioUrl = agent.opening_audio_url
            if (audioUrl.isNotBlank()) {
                audioUrls.add(audioUrl)
                EasyLog.log("AudioPreloadManager - 收集到音频URL: ${agent.name} -> $audioUrl")
            }
        }
        
        return audioUrls.toList()
    }
    
    /**
     * 并发预加载音频URL列表
     * @param audioUrls 音频URL列表
     * @param maxConcurrent 最大并发数
     */
    private suspend fun preloadAudioUrls(audioUrls: List<String>, maxConcurrent: Int) = coroutineScope {
        // 将URL列表分组，每组最多maxConcurrent个
        val chunks = audioUrls.chunked(maxConcurrent)
        
        chunks.forEach { chunk ->
            // 并发预加载当前组的所有音频
            val jobs = chunk.map { url ->
                async {
                    try {
                        // 检查是否已经缓存
                        if (!audioCacheManager.isCached(url)) {
                            audioCacheManager.preloadAudio(url)
                            EasyLog.log("AudioPreloadManager - 预加载音频成功: $url")
                        } else {
                            EasyLog.log("AudioPreloadManager - 音频已缓存，跳过: $url")
                        }
                    } catch (e: Exception) {
                        EasyLog.log("AudioPreloadManager - 预加载音频失败: $url, 错误: ${e.message}", EasyLog.ERROR)
                    }
                }
            }
            
            // 等待当前组的所有任务完成
            jobs.forEach { it.await() }
        }
    }
    
    /**
     * 检查音频是否已预加载
     * @param audioUrl 音频URL
     * @return 是否已缓存
     */
    fun isAudioPreloaded(audioUrl: String): Boolean {
        return if (isInitialized) {
            audioCacheManager.isCached(audioUrl)
        } else {
            false
        }
    }
    
    /**
     * 获取预加载状态
     */
    fun isInitialized(): Boolean {
        return isInitialized
    }
    
    /**
     * 清除预加载缓存
     */
    fun clearCache() {
        if (isInitialized) {
            audioCacheManager.clearCache()
            EasyLog.log("AudioPreloadManager - 清除预加载缓存")
        }
    }
    
    /**
     * 清理过期缓存
     */
    fun cleanExpiredCache() {
        if (isInitialized) {
            audioCacheManager.cleanExpiredCache()
            EasyLog.log("AudioPreloadManager - 清理过期缓存")
        }
    }
    
    /**
     * 获取缓存大小
     */
    fun getCacheSize(): Long {
        return if (isInitialized) {
            audioCacheManager.getCacheSize()
        } else {
            0L
        }
    }
}
