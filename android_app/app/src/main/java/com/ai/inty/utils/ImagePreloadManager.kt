package com.ai.inty.utils

import coil3.ImageLoader
import coil3.request.ImageRequest
import com.ai.inty.base.getGlobalImageLoader
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext

/**
 * 图片预加载管理器
 * 负责在后台预加载图片到缓存中，提升用户体验
 */
object ImagePreloadManager {
    
    private val imageLoader: ImageLoader by lazy { getGlobalImageLoader() }
    
    /**
     * 预加载单个图片
     * @param imageUrl 图片URL
     */
    suspend fun preloadImage(imageUrl: String) {
        if (imageUrl.isBlank()) return
        
        try {
            withContext(Dispatchers.IO) {
                val request = ImageRequest.Builder(AppEnv.context)
                    .data(imageUrl)
                    .build()
                
                imageLoader.enqueue(request)
                EasyLog.log("ImagePreloadManager - 预加载图片成功: $imageUrl")
            }
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 预加载图片失败: $imageUrl, 错误: ${e.message}")
        }
    }
    
    /**
     * 批量预加载图片
     * @param imageUrls 图片URL列表
     */
    suspend fun preloadImages(imageUrls: List<String>) {
        if (imageUrls.isEmpty()) return
        
        EasyLog.log("ImagePreloadManager - 开始批量预加载 ${imageUrls.size} 张图片")
        
        try {
            withContext(Dispatchers.IO) {
                coroutineScope {
                    // 并行预加载所有图片
                    val deferredResults = imageUrls.map { imageUrl ->
                        async {
                            if (imageUrl.isNotBlank()) {
                                try {
                                    val request = ImageRequest.Builder(AppEnv.context)
                                        .data(imageUrl)
                                        .build()
                                    
                                    imageLoader.enqueue(request)
                                    EasyLog.log("ImagePreloadManager - 预加载图片成功: $imageUrl")
                                    true
                                } catch (e: Exception) {
                                    EasyLog.log("ImagePreloadManager - 预加载图片失败: $imageUrl, 错误: ${e.message}")
                                    false
                                }
                            } else {
                                false
                            }
                        }
                    }
                    
                    // 等待所有预加载完成
                    val results = deferredResults.map { it.await() }
                    val successCount = results.count { it }
                    
                    EasyLog.log("ImagePreloadManager - 批量预加载完成: 成功 $successCount/${imageUrls.size} 张图片")
                }
            }
        } catch (e: Exception) {
            EasyLog.log("ImagePreloadManager - 批量预加载异常: ${e.message}")
        }
    }
    
    /**
     * 预加载角色图片
     * @param agents 角色信息列表
     */
    suspend fun preloadAgentImages(agents: List<com.ai.inty.beans.AgentInfo>) {
        val imageUrls = agents.mapNotNull { agent ->
            // 提取角色图片URL（background字段）
            agent.background?.takeIf { it.isNotBlank() }
        }
        
        if (imageUrls.isNotEmpty()) {
            EasyLog.log("ImagePreloadManager - 开始预加载 ${agents.size} 个角色的图片")
            preloadImages(imageUrls)
        }
    }
    
    /**
     * 预加载角色头像
     * @param agents 角色信息列表
     */
    suspend fun preloadAgentAvatars(agents: List<com.ai.inty.beans.AgentInfo>) {
        val imageUrls = agents.mapNotNull { agent ->
            // 提取角色头像URL（avatar字段）
            agent.avatar?.takeIf { it.isNotBlank() }
        }
        
        if (imageUrls.isNotEmpty()) {
            EasyLog.log("ImagePreloadManager - 开始预加载 ${agents.size} 个角色的头像")
            preloadImages(imageUrls)
        }
    }
    
    /**
     * 预加载角色的所有图片（背景图和头像）
     * @param agents 角色信息列表
     */
    suspend fun preloadAllAgentImages(agents: List<com.ai.inty.beans.AgentInfo>) {
        val allImageUrls = agents.flatMap { agent ->
            listOfNotNull(
                agent.background?.takeIf { it.isNotBlank() },
                agent.avatar?.takeIf { it.isNotBlank() }
            )
        }.distinct()
        
        if (allImageUrls.isNotEmpty()) {
            EasyLog.log("ImagePreloadManager - 开始预加载 ${agents.size} 个角色的所有图片")
            preloadImages(allImageUrls)
        }
    }
}
