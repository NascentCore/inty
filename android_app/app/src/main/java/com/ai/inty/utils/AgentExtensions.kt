package com.ai.inty.utils

import com.ai.inty.beans.AgentInfo

/** Extension functions for AgentInfo to handle avatar and background logic */

/** Get the chat background image URL Priority: background -> avatar */
fun AgentInfo.getChatBackground(): String? {
    return background.takeIf { it.isNotBlank() } ?: avatar.takeIf { it.isNotBlank() }
}
