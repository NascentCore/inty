package com.ai.intellimate.utils

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
    }

    fun setGeneratedAvatarUrls(urls: List<String>) {
        generatedAvatarUrls = urls
        generatedAvatarUrl = null // Clear single URL when setting multiple URLs
        selectedImageIndex = 0 // Reset selection to first image
        isGenerating = false
        generationError = null
    }

    fun setGenerationPrompt(prompt: String) {
        generationPrompt = prompt
        isGenerating = true
        generationError = null
    }

    fun setGenerationError(error: String) {
        generationError = error
        isGenerating = false
    }

    fun clearGeneratedAvatarUrl() {
        generatedAvatarUrl = null
        generatedAvatarUrls = emptyList()
        selectedImageIndex = 0
        isGenerating = false
        generationError = null
        generationPrompt = ""
        chatBackgroundUrl = null
    }

    fun clearAllAvatarData() {
        clearGeneratedAvatarUrl()
    }

    fun getCurrentAvatarUrl(): String? {
        return generatedAvatarUrl
    }

    fun getCurrentAvatarUrls(): List<String> {
        return generatedAvatarUrls
    }

    fun getSelectedImageIndex(): Int {
        return selectedImageIndex
    }

    fun setSelectedImageIndex(index: Int) {
        selectedImageIndex = index
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
    }
}
