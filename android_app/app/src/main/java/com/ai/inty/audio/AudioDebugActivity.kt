package com.ai.inty.audio

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.inty.utils.log.EasyLog

/**
 * 音频调试Activity
 * 用于测试音频播放功能
 */
class AudioDebugActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            AudioDebugScreen()
        }
    }
}

@Composable
fun AudioDebugScreen() {
    val context = LocalContext.current
    val audioManager = remember { AudioPlaybackManager.getInstance(context) }
    
    // 测试音频列表
    val testAudios = listOf(
        AudioInfo(
            url = "http://demo.fengxianqi.com/audio/static/opus.opus",
            title = "测试音频1",
            messageId = "test_1"
        ),
        AudioInfo(
            url = "http://demo.fengxianqi.com/audio/static/opus.opus",
            title = "测试音频2", 
            messageId = "test_2"
        ),
        AudioInfo(
            url = "http://demo.fengxianqi.com/audio/static/opus.opus",
            title = "测试音频3",
            messageId = "test_3"
        )
    )
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "音频播放调试",
            style = MaterialTheme.typography.headlineMedium
        )
        
        // 播放状态显示
        val playbackState by audioManager.playbackState.collectAsState()
        val currentAudioInfo = audioManager.getCurrentAudioInfo()
        
        Card {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("当前播放状态: $playbackState")
                Text("当前音频: ${currentAudioInfo?.messageId ?: "无"}")
                Text("是否正在播放: ${audioManager.isPlaying()}")
            }
        }
        
        // 测试音频列表
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(testAudios) { audioInfo ->
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = audioInfo.title ?: "未知音频",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text("Message ID: ${audioInfo.messageId}")
                        Text("URL: ${audioInfo.url}")
                        
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Button(
                                onClick = {
                                    EasyLog.log("Debug: Playing audio ${audioInfo.messageId}")
                                    audioManager.playAudio(audioInfo, autoPlay = true)
                                }
                            ) {
                                Text("播放")
                            }
                            
                            Button(
                                onClick = {
                                    EasyLog.log("Debug: Pausing audio")
                                    audioManager.pausePlayback()
                                }
                            ) {
                                Text("暂停")
                            }
                            
                            Button(
                                onClick = {
                                    EasyLog.log("Debug: Stopping audio")
                                    audioManager.stopPlayback()
                                }
                            ) {
                                Text("停止")
                            }
                        }
                        
                        // 使用VoicePlayer组件
                        VoicePlayer(
                            audioInfo = audioInfo,
                            autoPlay = false,
                            showProgress = true,
                            compact = true
                        )
                    }
                }
            }
        }
    }
}
