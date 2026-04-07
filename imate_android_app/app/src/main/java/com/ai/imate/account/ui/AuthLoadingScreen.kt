package com.ai.imate.account.ui

import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.imate.account.ui.viewmodel.LoginViewModel

@Composable
fun AuthLoadingScreen(
    onLoginSuccess: () -> Unit,
    viewModel: LoginViewModel = viewModel()
) {
    LaunchedEffect(Unit) {
        viewModel.isLogin
            .collect {

            }
    }

    LinearProgressIndicator(
        progress = {0f}
    )
}