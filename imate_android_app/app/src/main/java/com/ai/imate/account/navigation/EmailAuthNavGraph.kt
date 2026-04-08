package com.ai.imate.account.navigation

import android.app.Activity
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation3.runtime.NavKey
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.imate.account.ui.AuthLoadingScreen
import com.ai.imate.account.ui.EmailInputScreen
import com.ai.imate.account.ui.LoginScreen
import com.ai.imate.account.ui.PasswordInputScreen
import com.ai.imate.account.ui.viewmodel.LoginViewModel
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable

@Serializable
data object Login: NavKey

@Composable
fun EmailAuthNavHost(
    onLoginSuccess: () -> Unit,
    onOpenTerms: () -> Unit,
    onOpenPrivacy: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LoginViewModel = viewModel<LoginViewModel>(),
) {
    val backStack = rememberNavBackStack(EmailAuthRoute.Login)
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(Unit) {
        snapshotFlow { uiState.isLoading }
            .collect {
                if (it && backStack.lastOrNull() !is EmailAuthRoute.Loading) {
                    backStack.add(EmailAuthRoute.Loading)
                } else if (!it && backStack.lastOrNull() is EmailAuthRoute.Loading) {
                    backStack.removeLastOrNull()
                }
            }
    }

    NavDisplay(
        backStack = backStack,
        modifier = modifier.fillMaxSize(),
        onBack = {
            if (backStack.size > 1) {
                backStack.removeLastOrNull()
            } else {
                (context as? Activity)?.finish()
            }
        },
        transitionSpec = {
            // Slide in from right when navigating forward
            slideInHorizontally(initialOffsetX = { it }) togetherWith
                    slideOutHorizontally(targetOffsetX = { -it })
        },
        popTransitionSpec = {
            // Slide in from left when navigating back
            slideInHorizontally(initialOffsetX = { -it }) togetherWith
                    slideOutHorizontally(targetOffsetX = { it })
        },
        predictivePopTransitionSpec = {
            // Slide in from left when navigating back
            slideInHorizontally(initialOffsetX = { -it }) togetherWith
                    slideOutHorizontally(targetOffsetX = { it })
        },
        entryProvider = entryProvider<NavKey> {
            entry<EmailAuthRoute.Login> {
                LoginScreen(
                    onContinueWithEmail = {
                        backStack.add(EmailAuthRoute.EmailInput(""))
                    },
                    onContinueWithGoogle = { idToken ->
                        viewModel.googleLogin(idToken)
                    },
                    onTermsClick = onOpenTerms,
                    onPrivacyClick = onOpenPrivacy,
                    modifier = Modifier.fillMaxSize(),
                )
            }
            entry<EmailAuthRoute.EmailInput> { key ->
                EmailInputScreen(
                    onBack = { backStack.removeLastOrNull() },
                    onContinue = { email ->
                        if (backStack.lastOrNull() is EmailAuthRoute.Password) {
                            backStack.removeLastOrNull()
                        }
                        backStack.add(EmailAuthRoute.Password(email))
                    },
                    initialEmail = key.initialEmail,
                )
            }
            entry<EmailAuthRoute.Password> { key ->
                PasswordInputScreen(
                    email = key.email,
                    onBack = { backStack.removeLastOrNull() },
                    onLogin = { email, password ->
                        viewModel.emailLogin(email, password)
                    },
                )
            }
            entry<EmailAuthRoute.Loading> {
                AuthLoadingScreen(onLoginSuccess = onLoginSuccess)
            }
        },
    )
}
