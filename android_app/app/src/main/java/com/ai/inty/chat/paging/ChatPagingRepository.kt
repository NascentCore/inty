package com.ai.inty.chat.paging

import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import com.ai.inty.beans.AgentInfo
import com.ai.inty.chat.constants.ChatConstants
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.flow.Flow

/**
 * Chat页面的Paging数据仓库
 * 负责管理聊天agents的Paging数据流、配置和传统数据请求
 */
class ChatPagingRepository {

    companion object {
        // 使用统一的常量
        private const val PAGE_SIZE = ChatConstants.PAGE_SIZE
        private const val PREFETCH_DISTANCE = ChatConstants.PREFETCH_DISTANCE
        private const val ENABLE_PLACEHOLDERS = ChatConstants.ENABLE_PLACEHOLDERS
    }

    /**
     * 获取聊天agents的Paging数据流
     * @param useCache 是否使用缓存数据
     * @param sortSeed 排序种子，用于刷新时改变排序
     */
    fun getChatAgentsFlow(
        useCache: Boolean = true,
        sortSeed: Int = IntySetting.randomSortSeed()
    ): Flow<PagingData<AgentInfo>> {
        EasyLog.log("ChatPagingRepository - 创建Paging数据流，useCache: $useCache, sortSeed: $sortSeed")
        
        return Pager(
            config = PagingConfig(
                pageSize = PAGE_SIZE,
                prefetchDistance = PREFETCH_DISTANCE,
                enablePlaceholders = ENABLE_PLACEHOLDERS,
                initialLoadSize = PAGE_SIZE,
                maxSize = PAGE_SIZE * ChatConstants.MAX_CACHE_PAGES // 最大缓存页数
            ),
            pagingSourceFactory = {
                ChatPagingSource(
                    useCache = useCache,
                    sortSeed = sortSeed
                )
            }
        ).flow
    }

    /**
     * 刷新数据（生成新的排序种子）
     */
    fun refreshChatAgents(): Flow<PagingData<AgentInfo>> {
        val newSortSeed = IntySetting.randomSortSeed()
        EasyLog.log("ChatPagingRepository - 刷新数据，新randomSortSeed: $newSortSeed")
        
        return getChatAgentsFlow(
            useCache = false, // 刷新时不使用缓存
            sortSeed = newSortSeed
        )
    }

    /**
     * 获取初始数据（优先使用缓存）
     */
    fun getInitialChatAgents(): Flow<PagingData<AgentInfo>> {
        return getChatAgentsFlow(useCache = true)
    }
}
