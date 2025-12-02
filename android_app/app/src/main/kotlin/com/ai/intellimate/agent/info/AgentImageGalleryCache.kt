package com.ai.intellimate.agent.info

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

// CREATED_BY_AGENT
object AgentImageGalleryCache {

    private const val KEY_PREFIX_AGENT_GALLERY = "agent_gallery_images_"
    private val moshi =
        Moshi.Builder()
            .addLast(KotlinJsonAdapterFactory())
            .build()
    private val galleryType =
        Types.newParameterizedType(List::class.java, AgentImageGalleryItem::class.java)
    private val adapter = moshi.adapter<List<AgentImageGalleryItem>>(galleryType)

    fun getCachedGallery(agentId: String): List<AgentImageGalleryItem> {
        if (agentId.isBlank()) {
            return emptyList()
        }
        return runCatching {
            val json = IntySetting.getUserProfileData("$KEY_PREFIX_AGENT_GALLERY$agentId")
            if (json.isNullOrBlank()) {
                emptyList()
            } else {
                adapter.fromJson(json).orEmpty()
            }
        }.onFailure { throwable ->
            LogUtils.e(
                "AgentImageGalleryCache - restore failed for $agentId: ${throwable.message}"
            )
        }.getOrDefault(emptyList())
    }

    fun cacheGallery(agentId: String, items: List<AgentImageGalleryItem>) {
        if (agentId.isBlank()) {
            return
        }
        if (items.isEmpty()) {
            IntySetting.clearUserProfileData("$KEY_PREFIX_AGENT_GALLERY$agentId")
            return
        }
        runCatching {
            val json = adapter.toJson(items)
            IntySetting.setUserProfileData("$KEY_PREFIX_AGENT_GALLERY$agentId", json)
        }.onFailure { throwable ->
            LogUtils.e(
                "AgentImageGalleryCache - persist failed for $agentId: ${throwable.message}"
            )
        }
    }

    fun clearGallery(agentId: String) {
        if (agentId.isBlank()) {
            return
        }
        IntySetting.clearUserProfileData("$KEY_PREFIX_AGENT_GALLERY$agentId")
    }
}
