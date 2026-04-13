package com.inty.imate.account.navigation

import androidx.compose.runtime.Immutable
import androidx.navigation3.runtime.NavKey
import kotlinx.serialization.Serializable

@Immutable
sealed interface EmailAuthRoute : NavKey {

    @Serializable
    data object Loading: EmailAuthRoute

    @Serializable
    data object Login : EmailAuthRoute

    @Serializable
    data class EmailInput(val initialEmail: String = "") : EmailAuthRoute

    @Serializable
    data class Password(val email: String) : EmailAuthRoute
}
