package com.ai.intellimate.agent.heartbeat.viewmodel

import ai.sxwl.android.data.character.repository.CharacterRepository
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class HeartbeatViewModel : ViewModel() {

    private val repository = CharacterRepository()
    private val _agentId = MutableStateFlow<String?>(null)

    @OptIn(ExperimentalCoroutinesApi::class)
    val memories =
        _agentId
            .filterNotNull()
            .flatMapLatest { repository.getFestivalMemories(it) }
            .stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

    /** 角色名字（取 first name，用于标题等展示） */
    @OptIn(ExperimentalCoroutinesApi::class)
    val agentFirstName =
        _agentId
            .flatMapLatest { id ->
                if (id == null) flowOf(null)
                else
                    repository.observeCharacter(id).map { entity ->
                        entity
                            ?.name
                            ?.trim()
                            ?.takeIf { it.isNotBlank() }
                            ?.let { n ->
                                n.split(Regex("\\s+")).firstOrNull()?.takeIf { it.isNotBlank() }
                                    ?: n
                            }
                    }
            }
            .stateIn(viewModelScope, SharingStarted.Eagerly, null)

    fun setAgentId(agentId: String) {
        _agentId.value = agentId

        refreshAgent(agentId)
    }

    private fun refreshAgent(agentId: String) {
        viewModelScope.launch(Dispatchers.IO) { repository.refreshAgent(agentId) }
    }
}
