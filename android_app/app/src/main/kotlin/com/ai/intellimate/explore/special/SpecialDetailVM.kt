package com.ai.intellimate.explore.special

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.model.AgentInfo
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** 角色专区详情页面 ViewModel */
class CollectionDetailVM : BaseVM() {

    private val _themeTitle = MutableStateFlow("")
    val themeTitle: StateFlow<String> = _themeTitle.asStateFlow()

    private val _eventDescription = MutableStateFlow("")
    val eventDescription: StateFlow<String> = _eventDescription.asStateFlow()

    private val _isEventExpanded = MutableStateFlow(false)
    val isEventExpanded: StateFlow<Boolean> = _isEventExpanded.asStateFlow()

    private val _agents = MutableStateFlow<List<AgentInfo>>(emptyList())
    val agents: StateFlow<List<AgentInfo>> = _agents.asStateFlow()

    private val _isChristmas = MutableStateFlow(false)
    val isChristmas: StateFlow<Boolean> = _isChristmas.asStateFlow()

    fun setThemeData(
        title: String,
        description: String,
        agents: List<AgentInfo>,
        isChristmas: Boolean = false,
    ) {
        _themeTitle.value = title
        _eventDescription.value = description
        _agents.value = agents
        _isChristmas.value = isChristmas
    }

    fun toggleEventExpanded() {
        _isEventExpanded.value = !_isEventExpanded.value
    }
}
