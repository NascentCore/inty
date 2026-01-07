package com.ai.intellimate.utils

// CREATED_BY_AGENT: GPT-5.2 (Cursor Cloud Agent)

import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat

object ShareUtils {
    fun canShareAsUrl(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        return url.startsWith("http://") || url.startsWith("https://")
    }

    fun shareUrl(context: Context, url: String, chooserTitle: String? = null) {
        val sendIntent =
            Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, url)
            }
        val chooserIntent = Intent.createChooser(sendIntent, chooserTitle)
        ContextCompat.startActivity(context, chooserIntent, null)
    }
}
