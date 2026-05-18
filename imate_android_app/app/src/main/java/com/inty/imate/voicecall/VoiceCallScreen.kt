package com.inty.imate.voicecall

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CallEnd
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.inty.imate.R

/**
 * Full-screen in-app realtime voice-call surface.
 *
 * The surface is intentionally minimal: it starts a Live Chat WebSocket call for the selected
 * companion, streams microphone PCM to the backend, plays returned PCM, and lets the user end the
 * call. It is shown as an overlay from chat so returning to text chat does not require navigation.
 */
@Composable
fun VoiceCallScreen(
    agentId: String,
    agentName: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: VoiceCallViewModel = viewModel(),
) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsStateWithLifecycle()
    val remaining by viewModel.remainingSeconds.collectAsStateWithLifecycle()
    val error by viewModel.lastError.collectAsStateWithLifecycle()
    val launcher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) viewModel.start(agentId)
        }

    LaunchedEffect(agentId) {
        if (
            context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
        ) {
            viewModel.start(agentId)
        } else {
            launcher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(Color(0xFF15111D))
                .padding(28.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Box(
                modifier =
                    Modifier
                        .size(112.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.24f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = agentName.take(1).uppercase(),
                    color = Color.White,
                    style = MaterialTheme.typography.displaySmall,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(Modifier.height(24.dp))
            Text(
                text = agentName,
                color = Color.White,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text =
                    error
                        ?: when (state) {
                            VoiceCallConnectionState.CONNECTING -> stringResource(R.string.voice_call_connecting)
                            VoiceCallConnectionState.CONNECTED -> stringResource(R.string.voice_call_connected)
                            VoiceCallConnectionState.ERROR -> stringResource(R.string.voice_call_error)
                            VoiceCallConnectionState.DISCONNECTED -> stringResource(R.string.voice_call_ended)
                        },
                color = Color.White.copy(alpha = 0.72f),
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
            )
            remaining?.let {
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.voice_call_remaining_seconds, it),
                    color = Color.White.copy(alpha = 0.56f),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Spacer(Modifier.height(44.dp))
            Row(horizontalArrangement = Arrangement.Center) {
                IconButton(
                    onClick = {
                        viewModel.stop()
                        onDismiss()
                    },
                    modifier =
                        Modifier
                            .size(72.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.error),
                ) {
                    Icon(
                        imageVector = Icons.Outlined.CallEnd,
                        contentDescription = stringResource(R.string.voice_call_end),
                        tint = Color.White,
                    )
                }
            }
            if (state == VoiceCallConnectionState.ERROR || error != null) {
                Spacer(Modifier.height(24.dp))
                Button(onClick = onDismiss) { Text(stringResource(R.string.voice_call_close)) }
            }
        }
    }
}
