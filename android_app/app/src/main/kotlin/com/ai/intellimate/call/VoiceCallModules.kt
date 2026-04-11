package com.ai.intellimate.call

import ai.sxwl.android.data.di.networkModule
import ai.sxwl.android.inty.voicecall.IntyVoiceCallClient
import ai.sxwl.android.inty.voicecall.VoiceCallWebSocketDataSource
import com.ai.intellimate.call.data.AICallRepository
import org.koin.core.annotation.KoinExperimentalAPI
import org.koin.core.module.dsl.scopedOf
import org.koin.core.module.dsl.viewModelOf
import org.koin.dsl.module
import org.koin.viewmodel.scope.viewModelScope

@OptIn(KoinExperimentalAPI::class)
val voiceCallModule = module {
    includes(networkModule)
    viewModelOf(::VoiceCallViewModel)
    viewModelScope {
        scopedOf(::VoiceCallWebSocketDataSource)
        scopedOf(::IntyVoiceCallClient)
        scopedOf(::AICallRepository)
    }
}
