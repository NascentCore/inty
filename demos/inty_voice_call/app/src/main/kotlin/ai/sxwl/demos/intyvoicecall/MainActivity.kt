package ai.sxwl.demos.intyvoicecall

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    DemoScreen()
                }
            }
        }
    }
}

@Composable
private fun DemoScreen(vm: DemoViewModel = viewModel()) {
    val ctx = LocalContext.current
    val permissionLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            vm.setMicPermissionGranted(granted)
        }

    LaunchedEffect(Unit) {
        val granted =
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
        vm.setMicPermissionGranted(granted)
    }

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("Inty live chat voice demo", style = MaterialTheme.typography.titleLarge)
        OutlinedTextField(
            value = vm.ui.apiEndpoint,
            onValueChange = vm::updateEndpoint,
            label = { Text("API endpoint (https base, no trailing slash)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = vm.ui.apiKey,
            onValueChange = vm::updateApiKey,
            label = { Text("API key (JWT Bearer)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = vm.ui.agentId,
            onValueChange = vm::updateAgentId,
            label = { Text("Agent id") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = vm.ui.speechLanguageCode,
            onValueChange = vm::updateSpeechLanguage,
            label = { Text("Speech language code (BCP-47, e.g. en-US)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = vm.ui.responseLanguageName,
            onValueChange = vm::updateResponseLanguage,
            label = { Text("Response language name (e.g. English)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Text(vm.ui.statusLine, style = MaterialTheme.typography.bodyMedium)
        Button(
            onClick = { permissionLauncher.launch(Manifest.permission.RECORD_AUDIO) },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Request microphone permission")
        }
        Button(onClick = vm::checkStatus, modifier = Modifier.fillMaxWidth()) {
            Text("GET /api/v1/live-chat/status")
        }
        Button(
            onClick = vm::startCall,
            enabled = !vm.ui.inCall,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Start voice call")
        }
        Button(
            onClick = vm::stopCall,
            enabled = vm.ui.inCall,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Stop")
        }
        Text("Log", style = MaterialTheme.typography.labelLarge)
        Text(vm.ui.logTail, style = MaterialTheme.typography.bodySmall, modifier = Modifier.fillMaxWidth())
    }
}
