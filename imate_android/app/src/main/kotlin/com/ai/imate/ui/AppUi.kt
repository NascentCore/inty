package com.ai.imate.ui

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.ai.imate.R
import com.ai.imate.auth.AuthUiState
import com.ai.imate.chat.ChatUiState
import com.ai.imate.chat.MessageRole
import kotlinx.coroutines.launch

private object Route {
    const val LOGIN = "login"
    const val CHAT = "chat"
    const val SETTINGS = "settings"
}

private data class NavDestination(
    val route: String,
    val titleRes: Int,
    val icon: @Composable () -> Unit,
)

/**
 * iMate root composable.
 * Usage: place in activity setContent to drive login, chat and settings.
 * Visual expectation: one-screen login and a simple bottom-nav app shell.
 * Configurable inputs: auth state, chat state and callbacks for user actions.
 */
@Composable
fun IMateApp(
    authState: AuthUiState,
    chatState: ChatUiState,
    onEmailInputChanged: (String) -> Unit,
    onPasswordInputChanged: (String) -> Unit,
    onEmailPasswordLogin: () -> Unit,
    onGoogleLogin: suspend () -> Result<String>,
    onGoogleLoginToken: (String) -> Unit,
    onSendChat: () -> Unit,
    onChatInputChanged: (String) -> Unit,
    onClearChat: () -> Unit,
    onToggleOfficialAssistant: (Boolean) -> Unit,
    onLogout: () -> Unit,
) {
    val navController = rememberNavController()
    val snackbarHostState = remember { SnackbarHostState() }
    val context = LocalContext.current
    val hasSession = authState.session != null

    LaunchedEffect(hasSession) {
        navController.navigate(if (hasSession) Route.CHAT else Route.LOGIN) {
            popUpTo(navController.graph.findStartDestination().id) { inclusive = true }
            launchSingleTop = true
        }
    }

    LaunchedEffect(authState.errorMessage) {
        val message = authState.errorMessage ?: return@LaunchedEffect
        snackbarHostState.showSnackbar(message)
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            if (hasSession) {
                AppBottomBar(navController = navController)
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = if (hasSession) Route.CHAT else Route.LOGIN,
            modifier = Modifier.padding(innerPadding),
        ) {
            composable(Route.LOGIN) {
                LoginScreen(
                    authState = authState,
                    onEmailInputChanged = onEmailInputChanged,
                    onPasswordInputChanged = onPasswordInputChanged,
                    onEmailPasswordLogin = onEmailPasswordLogin,
                    onGoogleLoginClick = {
                        val result = onGoogleLogin()
                        result.onSuccess { token ->
                            onGoogleLoginToken(token)
                        }.onFailure { error ->
                            Toast.makeText(
                                context,
                                error.message ?: stringResource(R.string.login_error_invalid),
                                Toast.LENGTH_SHORT,
                            ).show()
                        }
                    },
                )
            }
            composable(Route.CHAT) {
                ChatScreen(
                    chatState = chatState,
                    officialAssistantEnabled = authState.officialAssistantEnabled,
                    onSendChat = onSendChat,
                    onChatInputChanged = onChatInputChanged,
                )
            }
            composable(Route.SETTINGS) {
                SettingsScreen(
                    authState = authState,
                    onToggleOfficialAssistant = onToggleOfficialAssistant,
                    onClearChat = onClearChat,
                    onLogout = onLogout,
                )
            }
        }
    }
}

/**
 * Login screen for Google and reviewer email/password path.
 * Usage: first screen for unauthenticated user.
 * Visual expectation: centered card with two login methods.
 * Configurable inputs: form state and click callbacks.
 */
@Composable
private fun LoginScreen(
    authState: AuthUiState,
    onEmailInputChanged: (String) -> Unit,
    onPasswordInputChanged: (String) -> Unit,
    onEmailPasswordLogin: () -> Unit,
    onGoogleLoginClick: suspend () -> Unit,
) {
    val spaceLg = dimensionResource(R.dimen.space_lg)
    val spaceMd = dimensionResource(R.dimen.space_md)
    val buttonHeight = dimensionResource(R.dimen.button_height)
    val scope = rememberCoroutineScope()

    Box(
        modifier =
            Modifier.fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(spaceLg),
        contentAlignment = Alignment.Center,
    ) {
        Card(shape = MaterialTheme.shapes.large) {
            Column(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(spaceLg),
                verticalArrangement = Arrangement.spacedBy(spaceMd),
            ) {
                Text(
                    text = stringResource(R.string.login_title),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = stringResource(R.string.login_google_cn),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Button(
                    onClick = { scope.launch { onGoogleLoginClick() } },
                    enabled = !authState.isLoading,
                    modifier = Modifier.fillMaxWidth().height(buttonHeight),
                    contentPadding = PaddingValues(horizontal = spaceMd),
                ) {
                    Text("${stringResource(R.string.login_google)} / ${stringResource(R.string.login_google_cn)}")
                }

                Text(
                    text = "${stringResource(R.string.login_email_password)} / ${stringResource(R.string.login_email_password_cn)}",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedTextField(
                    value = authState.emailInput,
                    onValueChange = onEmailInputChanged,
                    label = {
                        Text("${stringResource(R.string.email_label)} / ${stringResource(R.string.email_label_cn)}")
                    },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = authState.passwordInput,
                    onValueChange = onPasswordInputChanged,
                    label = {
                        Text("${stringResource(R.string.password_label)} / ${stringResource(R.string.password_label_cn)}")
                    },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = onEmailPasswordLogin,
                    enabled = !authState.isLoading,
                    modifier = Modifier.fillMaxWidth().height(buttonHeight),
                ) {
                    Text("${stringResource(R.string.login_button)} / ${stringResource(R.string.login_button_cn)}")
                }
            }
        }
    }
}

/**
 * Chat screen for user and official assistant conversation.
 * Usage: primary app content after login.
 * Visual expectation: top title, scrollable messages, bottom input row.
 * Configurable inputs: messages list, input and send callback.
 */
@Composable
private fun ChatScreen(
    chatState: ChatUiState,
    officialAssistantEnabled: Boolean,
    onSendChat: () -> Unit,
    onChatInputChanged: (String) -> Unit,
) {
    val spaceSm = dimensionResource(R.dimen.space_sm)
    val spaceMd = dimensionResource(R.dimen.space_md)

    Column(
        modifier = Modifier.fillMaxSize().padding(spaceMd),
        verticalArrangement = Arrangement.spacedBy(spaceSm),
    ) {
        Text(
            text = "${stringResource(R.string.chat_title)} / ${stringResource(R.string.chat_title_cn)}",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text =
                if (officialAssistantEnabled) {
                    "${stringResource(R.string.official_assistant_enabled)} / ${stringResource(R.string.official_assistant_enabled_cn)}"
                } else {
                    "${stringResource(R.string.official_assistant_disabled)} / ${stringResource(R.string.official_assistant_disabled_cn)}"
                },
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(spaceSm),
        ) {
            items(chatState.messages, key = { it.id }) { message ->
                val title =
                    if (message.role == MessageRole.USER) {
                        "${stringResource(R.string.role_user)} / ${stringResource(R.string.role_user_cn)}"
                    } else {
                        "${stringResource(R.string.role_official_assistant)} / ${stringResource(R.string.role_official_assistant_cn)}"
                    }
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(spaceMd)) {
                        Text(
                            text = title,
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Spacer(modifier = Modifier.height(dimensionResource(R.dimen.space_xs)))
                        Text(text = message.content, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(spaceSm),
        ) {
            OutlinedTextField(
                value = chatState.input,
                onValueChange = onChatInputChanged,
                placeholder = {
                    Text("${stringResource(R.string.chat_input_hint)} / ${stringResource(R.string.chat_input_hint_cn)}")
                },
                modifier = Modifier.weight(1f),
                singleLine = true,
            )
            Button(onClick = onSendChat) {
                Text("${stringResource(R.string.chat_send)} / ${stringResource(R.string.chat_send_cn)}")
            }
        }
    }
}

/**
 * Settings screen with account info and reviewer support controls.
 * Usage: secondary tab after login.
 * Visual expectation: simple preference-like list.
 * Configurable inputs: session state and setting callbacks.
 */
@Composable
private fun SettingsScreen(
    authState: AuthUiState,
    onToggleOfficialAssistant: (Boolean) -> Unit,
    onClearChat: () -> Unit,
    onLogout: () -> Unit,
) {
    val spaceMd = dimensionResource(R.dimen.space_md)
    val session = authState.session

    Column(
        modifier = Modifier.fillMaxSize().padding(spaceMd),
        verticalArrangement = Arrangement.spacedBy(spaceMd),
    ) {
        Text(
            text = "${stringResource(R.string.settings_title)} / ${stringResource(R.string.settings_title_cn)}",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text =
                "${stringResource(R.string.settings_user_label)} / ${stringResource(R.string.settings_user_label_cn)}: " +
                    "${session?.nickname.orEmpty()} (${session?.email.orEmpty()})",
            style = MaterialTheme.typography.bodyMedium,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                text =
                    "${stringResource(R.string.settings_official_assistant)} / " +
                        stringResource(R.string.settings_official_assistant_cn)
            )
            Switch(
                checked = authState.officialAssistantEnabled,
                onCheckedChange = onToggleOfficialAssistant,
            )
        }
        Button(onClick = onClearChat, modifier = Modifier.fillMaxWidth()) {
            Text("${stringResource(R.string.settings_clear_chat)} / ${stringResource(R.string.settings_clear_chat_cn)}")
        }
        Button(onClick = onLogout, modifier = Modifier.fillMaxWidth()) {
            Text("${stringResource(R.string.logout_button)} / ${stringResource(R.string.logout_button_cn)}")
        }
    }
}

@Composable
private fun AppBottomBar(navController: NavHostController) {
    val navDestinations =
        listOf(
            NavDestination(
                route = Route.CHAT,
                titleRes = R.string.nav_chat,
                icon = { androidx.compose.material3.Icon(Icons.AutoMirrored.Filled.Chat, null) },
            ),
            NavDestination(
                route = Route.SETTINGS,
                titleRes = R.string.nav_settings,
                icon = { androidx.compose.material3.Icon(Icons.Filled.Settings, null) },
            ),
        )
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val selectedRoute = navBackStackEntry?.destination?.route

    NavigationBar {
        navDestinations.forEach { destination ->
            NavigationBarItem(
                selected = selectedRoute == destination.route,
                onClick = {
                    navController.navigate(destination.route) {
                        popUpTo(navController.graph.findStartDestination().id) {
                            saveState = true
                        }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
                icon = destination.icon,
                label = { Text(stringResource(destination.titleRes)) },
            )
        }
    }
}
