package com.ai.inty.utils

import android.content.Context
import com.ai.inty.beans.AgentInfo
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * 图片预加载管理器
 * 负责在启动时预加载agents的图片资源，优化Explore页面渲染体验
 */
object ImagePreloadManager {
    
    private var isInitialized = false
    
    /**
     * 初始化图片预加载管理器
     */
    fun init(context: Context) {
        if (isInitialized) return
        
        ImageSizeCache.init(context)
        StableCardHeightManager.init(context)
        isInitialized = true
        EasyLog.log("ImagePreloadManager - 初始化完成")
    }
    
    /**
     * 预加载agents的图片资源
     * @param agents 需要预加载的agents列表
     * @param maxConcurrent 最大并发预加载数量
     */
    suspend fun preloadAgentsImages(
        agents: List<AgentInfo>,
        maxConcurrent: Int = 5
    ) {
        if (!isInitialized) {
            EasyLog.log("ImagePreloadManager - 未初始化，跳过预加载", EasyLog.WARN)
            return
        }
        
        if (agents.isEmpty()) {
            EasyLog.log("ImagePreloadManager - agents列表为空，跳过预加载")
            return
        }
        
        EasyLog.log("ImagePreloadManager - 开始预加载 ${agents.size} 个agents的图片资源")
        
        try {
            withContext(Dispatchers.IO) {
                // 收集所有需要预加载的图片URL
                val imageUrls = collectImageUrls(agents)
                EasyLog.log("ImagePreloadManager - 收集到 ${imageUrls.size} 个图片URL")
                
                if (imageUrls.isNotEmpty()) {
                    // 使用批量预加载方法，提高效率
                    ImageSizeCache.preloadImageSizes(imageUrls)
                    StableCardHeightManager.preloadImageSizes(imageUrls)
                    EasyLog.log("ImagePreloadManager - 批量预加载图片尺寸完成")
                }
            }
            
            EasyLog.log("ImagePreloadManager - 所有图片预加载完成")
            
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 预加载异常: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 收集agents中的所有图片URL
     * 使用与ExploreCharacterCard相同的逻辑，确保URL一致性
     */
    private fun collectImageUrls(agents: List<AgentInfo>): List<String> {
        val imageUrls = mutableSetOf<String>()
        
        agents.forEach { agent ->
            // 使用与ExploreCharacterCard相同的逻辑获取图片URL
            // 优先级：background -> avatar
            val imageUrl = AvatarManager.getChatBackgroundForAgent(agent)
            imageUrl?.takeIf { it.isNotBlank() }?.let { imageUrls.add(it) }
        }
        
        return imageUrls.toList()
    }
    
    /**
     * 预加载关键图片（前几屏的图片）
     * @param agents 需要预加载的agents列表
     * @param criticalCount 关键图片数量（前几屏）
     */
    suspend fun preloadCriticalImages(
        agents: List<AgentInfo>,
        criticalCount: Int = 10
    ) {
        if (!isInitialized) {
            EasyLog.log("ImagePreloadManager - 未初始化，跳过关键图片预加载", EasyLog.WARN)
            return
        }
        
        val criticalAgents = agents.take(criticalCount)
        if (criticalAgents.isEmpty()) {
            EasyLog.log("ImagePreloadManager - 关键agents列表为空，跳过预加载")
            return
        }
        
        EasyLog.log("ImagePreloadManager - 开始预加载前 $criticalCount 个关键图片")
        
        try {
            withContext(Dispatchers.IO) {
                val imageUrls = collectImageUrls(criticalAgents)
                
                if (imageUrls.isNotEmpty()) {
                    // 使用批量预加载方法，优先预加载关键图片
                    ImageSizeCache.preloadCriticalImageSizes(imageUrls, criticalCount)
                    StableCardHeightManager.preloadImageSizes(imageUrls)
                    EasyLog.log("ImagePreloadManager - 关键图片批量预加载完成")
                }
            }
            
            EasyLog.log("ImagePreloadManager - 关键图片预加载完成")
            
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 关键图片预加载异常: ${e.message}", EasyLog.ERROR)
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
        ImageSizeCache.clearCache()
        StableCardHeightManager.clearCache()
        EasyLog.log("ImagePreloadManager - 清除预加载缓存")
    }
}
