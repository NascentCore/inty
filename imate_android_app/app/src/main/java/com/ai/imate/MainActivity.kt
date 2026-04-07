package com.ai.imate

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import com.ai.core.ui.theme.IMateTheme
import com.ai.imate.auth.GoogleSignInHelper
import com.ai.imate.ui.login.LoginScreen
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            IMateTheme {
                val scope = rememberCoroutineScope()
                var isSigningIn by remember { mutableStateOf(false) }
                LoginScreen(
                    isSigningIn = isSigningIn,
                    onContinueWithGoogle = {
                        scope.launch {
                            isSigningIn = true
                            try {
                                GoogleSignInHelper.signInWithGoogle(this@MainActivity)
                            } finally {
                                isSigningIn = false
                            }
                        }
                    },
                    onTermsClick = {
                        openUrl(getString(R.string.login_terms_url))
                    },
                    onPrivacyClick = {
                        openUrl(getString(R.string.login_privacy_url))
                    },
                )
            }
        }
    }

    private fun openUrl(url: String) {
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }
}
