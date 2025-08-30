package com.ai.inty.base

import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed

/**
 * Anti-continuous click utility for preventing rapid button clicks
 */
object AntiClick {
    private const val CLICK_INTERVAL = 1000L // 1 second
    
    fun isValidClick(lastClickTime: Long): Boolean {
        val currentTime = System.currentTimeMillis()
        return currentTime - lastClickTime >= CLICK_INTERVAL
    }
}

fun Modifier.noRippleClickable(onClick: () -> Unit): Modifier = composed {
    var lastClickTime by remember { mutableLongStateOf(0L) }
    
    clickable(
        indication = null,
        interactionSource = remember { MutableInteractionSource() }) {
        val currentTime = System.currentTimeMillis()
        if (AntiClick.isValidClick(lastClickTime)) {
            lastClickTime = currentTime
            onClick()
        }
    }
}

/**
 * Standard clickable with anti-continuous click protection
 */
fun Modifier.safeClickable(onClick: () -> Unit): Modifier = composed {
    var lastClickTime by remember { mutableLongStateOf(0L) }
    
    clickable {
        val currentTime = System.currentTimeMillis()
        if (AntiClick.isValidClick(lastClickTime)) {
            lastClickTime = currentTime
            onClick()
        }
    }
}
