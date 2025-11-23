package com.ai.intellimate.utils

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo

// CREATED_BY_AGENT

/**
 * Agent 媒体内存缓存，记录已预加载的图片、开场白音频与背景视频 URL，避免重复触发下载。
 *
 * 该缓存只在 App 运行期生效，不做持久化；通过限定容量的 LRU 策略控制内存占用。
 */
object AgentMediaCache {

    private const val MAX_IMAGE_URLS = 256
    private const val MAX_AUDIO_URLS = 256
    private const val MAX_VIDEO_URLS = 128
    private const val STATIC_BACKGROUND_WIDTH = 1080
    private const val STATIC_BACKGROUND_QUALITY = 80

    private val lock = Any()

    private val cachedImageUrls = LinkedHashSet<String>()
    private val cachedAudioUrls = LinkedHashSet<String>()
    private val cachedVideoUrls = LinkedHashSet<String>()

    private val imageEvictionQueue = ArrayDeque<String>()
    private val audioEvictionQueue = ArrayDeque<String>()
    private val videoEvictionQueue = ArrayDeque<String>()

    /** 返回仍需预加载图片资源的 Agent 列表。 */
    fun filterAgentsNeedingImages(agents: List<AgentInfo>): List<AgentInfo> {
        return filterAgentsByUrls(agents, cachedImageUrls, ::collectImageUrls)
    }

    /** 返回仍需预加载开场白音频资源的 Agent 列表。 */
    fun filterAgentsNeedingOpeningAudios(agents: List<AgentInfo>): List<AgentInfo> {
        return filterAgentsByUrls(agents, cachedAudioUrls, ::collectOpeningAudioUrls)
    }

    /** 返回仍需预加载背景视频资源的 Agent 列表。 */
    fun filterAgentsNeedingBackgroundVideos(agents: List<AgentInfo>): List<AgentInfo> {
        return filterAgentsByUrls(agents, cachedVideoUrls, ::collectVideoUrls)
    }

    /** 将指定 Agent 的图片资源标记为已缓存。 */
    fun markImagesCached(agents: List<AgentInfo>) {
        markUrlsCached(agents, cachedImageUrls, imageEvictionQueue, MAX_IMAGE_URLS, ::collectImageUrls)
    }

    /** 将指定 Agent 的开场白音频资源标记为已缓存。 */
    fun markOpeningAudiosCached(agents: List<AgentInfo>) {
        markUrlsCached(
            agents,
            cachedAudioUrls,
            audioEvictionQueue,
            MAX_AUDIO_URLS,
            ::collectOpeningAudioUrls,
        )
    }

    /** 将指定 Agent 的背景视频资源标记为已缓存。 */
    fun markBackgroundVideosCached(agents: List<AgentInfo>) {
        markUrlsCached(
            agents,
            cachedVideoUrls,
            videoEvictionQueue,
            MAX_VIDEO_URLS,
            ::collectVideoUrls,
        )
    }

    /** 清空所有缓存记录。 */
    fun clear() {
        synchronized(lock) {
            cachedImageUrls.clear()
            cachedAudioUrls.clear()
            cachedVideoUrls.clear()
            imageEvictionQueue.clear()
            audioEvictionQueue.clear()
            videoEvictionQueue.clear()
        }
    }

    private fun filterAgentsByUrls(
        agents: List<AgentInfo>,
        cache: LinkedHashSet<String>,
        urlProvider: (AgentInfo) -> Set<String>,
    ): List<AgentInfo> {
        if (agents.isEmpty()) {
            return emptyList()
        }

        val urlPairs = agents.map { agent -> agent to urlProvider(agent) }
        val result = mutableListOf<AgentInfo>()

        synchronized(lock) {
            urlPairs.forEach { (agent, urls) ->
                if (urls.isEmpty()) {
                    return@forEach
                }
                if (urls.any { it.isNotBlank() && !cache.contains(it) }) {
                    result.add(agent)
                }
            }
        }

        return result
    }

    private fun markUrlsCached(
        agents: List<AgentInfo>,
        cache: LinkedHashSet<String>,
        evictionQueue: ArrayDeque<String>,
        maxSize: Int,
        urlProvider: (AgentInfo) -> Set<String>,
    ) {
        if (agents.isEmpty()) {
            return
        }

        val urlsToCache = agents.flatMap { urlProvider(it) }.filter { it.isNotBlank() }
        if (urlsToCache.isEmpty()) {
            return
        }

        synchronized(lock) {
            urlsToCache.forEach { url ->
                if (cache.add(url)) {
                    evictionQueue.addLast(url)
                }
                trimIfNeeded(cache, evictionQueue, maxSize)
            }
        }
    }

    private fun collectImageUrls(agent: AgentInfo): Set<String> {
        val urls = LinkedHashSet<String>()

        agent.getAlbumImage()?.takeIf { it.isNotBlank() }?.let(urls::add)

        val originImage = agent.getOriginShowImage()
        if (!originImage.isNullOrBlank()) {
            val optimized =
                getCdnImageUrl(
                    originImage,
                    width = STATIC_BACKGROUND_WIDTH,
                    quality = STATIC_BACKGROUND_QUALITY,
                ) ?: originImage
            urls.add(optimized)
        }

        if (agent.backgroundImages.isNotEmpty()) {
            agent.backgroundImages
                .filterNotNull()
                .filter { it.isNotBlank() }
                .map { bg ->
                    getCdnImageUrl(
                        bg,
                        width = STATIC_BACKGROUND_WIDTH,
                        quality = STATIC_BACKGROUND_QUALITY,
                    ) ?: bg
                }
                .forEach(urls::add)
        }

        return urls
    }

    private fun collectOpeningAudioUrls(agent: AgentInfo): Set<String> {
        val urls = LinkedHashSet<String>()
        if (agent.opening_audio_url.isNotBlank()) {
            urls.add(agent.opening_audio_url)
        }
        if (agent.voicePreview.isNotBlank()) {
            urls.add(agent.voicePreview)
        }
        return urls
    }

    private fun collectVideoUrls(agent: AgentInfo): Set<String> {
        val urls = LinkedHashSet<String>()
        if (agent.backgroundAnimatedUrl.isNotBlank()) {
            urls.add(agent.backgroundAnimatedUrl)
        }
        return urls
    }

    private fun trimIfNeeded(
        cache: LinkedHashSet<String>,
        evictionQueue: ArrayDeque<String>,
        maxSize: Int,
    ) {
        while (cache.size > maxSize && evictionQueue.isNotEmpty()) {
            val removed = evictionQueue.removeFirst()
            cache.remove(removed)
        }
    }
}
