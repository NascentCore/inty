package com.ai.imate

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.core.ui.theme.IMateTheme
import com.ai.core.utils.ToastUtils
import kotlinx.coroutines.flow.filterNotNull

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            IMateTheme {
            }

            LaunchedEffect(Unit) {
                GlobalErrorHandler.error
                    .filterNotNull()
                    .collect {
                        val message = it.message
                        if (!message.isNullOrEmpty()) {
                            ToastUtils.showShort(message)
                        }
                    }
            }
        }
    }

    private fun openUrl(url: String) {
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }
}
