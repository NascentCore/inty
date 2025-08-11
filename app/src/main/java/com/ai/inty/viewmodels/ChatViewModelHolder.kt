package com.ai.inty.viewmodels

import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore

/**
 * Provides shared ChatViewModel instances keyed by agentId so that
 * ChatActivity and the in-tab ChatPageContainer reuse the same state.
 */
object ChatViewModelHolder {
    private val storeMap = mutableMapOf<String, ViewModelStore>()

    fun get(agentId: String): ChatViewModel {
        val store = storeMap.getOrPut(agentId) { ViewModelStore() }
        val provider = ViewModelProvider(store, ViewModelProvider.NewInstanceFactory())
        return provider[ChatViewModel::class.java]
    }
}
