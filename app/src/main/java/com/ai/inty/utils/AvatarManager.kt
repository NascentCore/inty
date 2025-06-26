package com.ai.inty.utils

object AvatarManager {
    
    private var generatedAvatarUrl: String? = null
    
    fun setGeneratedAvatarUrl(url: String) {
        generatedAvatarUrl = url
        com.inty.utils.log.EasyLog.log("AvatarManager: Set generated avatar URL: $url")
    }
    
    fun getAndClearGeneratedAvatarUrl(): String? {
        val url = generatedAvatarUrl
        generatedAvatarUrl = null
        com.inty.utils.log.EasyLog.log("AvatarManager: Retrieved and cleared avatar URL: $url")
        return url
    }
    
    fun clearGeneratedAvatarUrl() {
        generatedAvatarUrl = null
        com.inty.utils.log.EasyLog.log("AvatarManager: Cleared avatar URL")
    }
    
    fun getCurrentAvatarUrl(): String? {
        com.inty.utils.log.EasyLog.log("AvatarManager: Current avatar URL: $generatedAvatarUrl")
        return generatedAvatarUrl
    }
}