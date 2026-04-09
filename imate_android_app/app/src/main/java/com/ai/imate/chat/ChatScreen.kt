package com.ai.imate.chat

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation3.runtime.NavKey
import kotlinx.serialization.Serializable

@Serializable
data object Chat: NavKey

@Composable
fun ChatScreen(modifier: Modifier = Modifier) {
    Text("聊天界面", modifier = modifier)
}