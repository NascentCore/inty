package com.ai.intellimate.utils

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.ToastUtils
import com.ai.intellimate.R

/**
 * 聊天背景工具类
 * 提供聊天背景图片的设置和清除功能
 */
object ChatBackgroundUtils {
    /**
     * 切换聊天背景图片
     * 如果当前图片已经是背景，则清除背景；否则设置为背景
     *
     * @param agentId 角色ID
     * @param imageUrl 图片URL
     * @param isCurrentBackground 当前图片是否已经是背景
     * @return 设置后的背景URL，清除时返回null
     */
    fun toggleChatBackground(
        agentId: String,
        imageUrl: String,
        isCurrentBackground: Boolean,
    ): String? {
        return if (isCurrentBackground) {
            clearChatBackground(agentId)
        } else {
            setChatBackground(agentId, imageUrl)
        }
    }

    /**
     * 设置聊天背景图片
     *
     * @param agentId 角色ID
     * @param imageUrl 图片URL
     * @return 设置的背景URL
     */
    fun setChatBackground(agentId: String, imageUrl: String): String {
        IntySetting.setChatBackgroundImage(agentId, imageUrl)
        ToastUtils.showShort(R.string.agent_gallery_background_set_success)
        return imageUrl
    }

    /**
     * 清除聊天背景图片
     *
     * @param agentId 角色ID
     * @return null（表示已清除）
     */
    fun clearChatBackground(agentId: String): String? {
        IntySetting.clearChatBackgroundImage(agentId)
        ToastUtils.showShort(R.string.agent_gallery_background_reset_success)
        return null
    }
}

