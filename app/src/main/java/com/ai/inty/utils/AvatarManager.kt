package com.ai.inty.utils

object AvatarManager {
    
    private var generatedAvatarUrl: String? = null
    private var generatedAvatarUrls: List<String> = emptyList()
    private var selectedImageIndex: Int = 0
    private var generationPrompt: String = ""
    private var isGenerating: Boolean = false
    private var generationError: String? = null
    private var chatBackgroundUrl: String? = null
    
    fun setGeneratedAvatarUrl(url: String) {
        generatedAvatarUrl = url
        generatedAvatarUrls = emptyList() // Clear multiple URLs when setting single URL
        com.inty.utils.log.EasyLog.log("AvatarManager: Set generated avatar URL: $url")
    }
    
    fun setGeneratedAvatarUrls(urls: List<String>) {
        generatedAvatarUrls = urls
        generatedAvatarUrl = null // Clear single URL when setting multiple URLs
        selectedImageIndex = 0 // Reset selection to first image
        isGenerating = false
        generationError = null
        com.inty.utils.log.EasyLog.log("AvatarManager: Set generated avatar URLs: $urls")
    }
    
    fun setGenerationPrompt(prompt: String) {
        generationPrompt = prompt
        isGenerating = true
        generationError = null
        com.inty.utils.log.EasyLog.log("AvatarManager: Set generation prompt and started generating")
    }
    
    fun setGenerationError(error: String) {
        generationError = error
        isGenerating = false
        com.inty.utils.log.EasyLog.log("AvatarManager: Set generation error: $error")
    }
    
    fun getAndClearGeneratedAvatarUrl(): String? {
        val url = generatedAvatarUrl
        generatedAvatarUrl = null
        com.inty.utils.log.EasyLog.log("AvatarManager: Retrieved and cleared avatar URL: $url")
        return url
    }
    
    fun clearGeneratedAvatarUrl() {
        generatedAvatarUrl = null
        generatedAvatarUrls = emptyList()
        selectedImageIndex = 0
        isGenerating = false
        generationError = null
        generationPrompt = ""
        chatBackgroundUrl = null
        com.inty.utils.log.EasyLog.log("AvatarManager: Cleared all avatar data")
    }
    
    fun clearAllAvatarData() {
        clearGeneratedAvatarUrl()
        com.inty.utils.log.EasyLog.log("AvatarManager: Cleared all avatar and background data")
    }
    
    fun getCurrentAvatarUrl(): String? {
        com.inty.utils.log.EasyLog.log("AvatarManager: Current avatar URL: $generatedAvatarUrl")
        return generatedAvatarUrl
    }
    
    fun getCurrentAvatarUrls(): List<String> {
        com.inty.utils.log.EasyLog.log("AvatarManager: Current avatar URLs: $generatedAvatarUrls")
        return generatedAvatarUrls
    }
    
    fun getSelectedImageIndex(): Int {
        return selectedImageIndex
    }
    
    fun setSelectedImageIndex(index: Int) {
        selectedImageIndex = index
        com.inty.utils.log.EasyLog.log("AvatarManager: Set selected image index: $index")
    }
    
    fun getSelectedAvatarUrl(): String? {
        return when {
            generatedAvatarUrls.isNotEmpty() && selectedImageIndex < generatedAvatarUrls.size -> {
                generatedAvatarUrls[selectedImageIndex]
            }
            generatedAvatarUrl != null -> generatedAvatarUrl
            else -> null
        }
    }
    
    fun isGenerating(): Boolean {
        return isGenerating
    }
    
    fun getGenerationPrompt(): String {
        return generationPrompt
    }
    
    fun getGenerationError(): String? {
        val error = generationError
        generationError = null // Clear error after reading
        return error
    }
    
    fun setChatBackgroundUrl(url: String) {
        chatBackgroundUrl = url
        com.inty.utils.log.EasyLog.log("AvatarManager: Set chat background URL: $url")
    }
    
    fun getChatBackgroundUrl(): String? {
        return chatBackgroundUrl
    }
    
    fun clearChatBackground() {
        chatBackgroundUrl = null
        com.inty.utils.log.EasyLog.log("AvatarManager: Cleared chat background URL")
    }
    
    // Helper functions for chat and avatar display logic
    fun getChatBackgroundForAgent(agent: com.ai.inty.beans.AgentInfo): String? {
        // Priority: background -> avatar
        return agent.background.takeIf { it.isNotBlank() } ?: agent.avatar.takeIf { it.isNotBlank() }
    }
    
    fun getAvatarForAgent(agent: com.ai.inty.beans.AgentInfo): String? {
        // Priority: avatar -> background
        return agent.avatar.takeIf { it.isNotBlank() } ?: agent.background.takeIf { it.isNotBlank() }
    }
}