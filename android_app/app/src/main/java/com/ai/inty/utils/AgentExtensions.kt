package com.ai.inty.utils

import com.ai.inty.beans.AgentInfo

/**
 * Extension functions for AgentInfo to handle avatar and background logic
 */

/**
 * Get the chat background image URL
 * Priority: background -> avatar
 */
fun AgentInfo.getChatBackground(): String? {
    return background.takeIf { it.isNotBlank() } ?: avatar.takeIf { it.isNotBlank() }
}

/**
 * Get the avatar image URL for display
 * Priority: avatar -> background
 */
fun AgentInfo.getDisplayAvatar(): String? {
    return avatar.takeIf { it.isNotBlank() } ?: background.takeIf { it.isNotBlank() }
}

/**
 * Check if agent has any image (avatar or background)
 */
fun AgentInfo.hasAnyImage(): Boolean {
    return avatar.isNotBlank() || background.isNotBlank()
}

/**
 * Check if agent has background images
 */
fun AgentInfo.hasBackgroundImages(): Boolean {
    return backgroundImages.isNotEmpty()
}