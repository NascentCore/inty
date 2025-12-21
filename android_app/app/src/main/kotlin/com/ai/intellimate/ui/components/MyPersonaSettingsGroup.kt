package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.design.ui.IntelliMateDivider
import ai.sxwl.android.design.ui.SettingsArrowItem
import ai.sxwl.android.design.ui.SettingsItemData
import ai.sxwl.android.design.ui.SettingsItemGroup
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.ai.intellimate.R

/**
 * CREATED_BY_AGENT: GPT-5.2
 *
 * My Persona 统一设置项（Name / Pronouns / Personality / Persona Description）。
 * 用于在 ChatSettingsDrawer 与 Edit My Persona 页面复用同一段渲染代码。
 */
private const val DEFAULT_GUEST_NAME = "Guest"

@Composable
fun MyPersonaSettingsGroup(
    userProfile: UserProfile,
    preference: String,
    modifier: Modifier = Modifier,
    horizontalPadding: Int = 16,
    fontLight: Boolean = false,
    contentMaxLines: Int = 1,
    onClickName: () -> Unit,
    onClickPronouns: () -> Unit,
    onClickPreference: () -> Unit,
    onClickPersona: () -> Unit,
) {
    val personaContent =
        userProfile.description?.takeIf { it.isNotBlank() } ?: stringResource(R.string.edit_button)
    val preferenceContent =
        preference.ifBlank { stringResource(R.string.chat_settings_preference_placeholder) }

    SettingsItemGroup(modifier = modifier) {
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.str_name),
                    content = userProfile.nickname.ifEmpty { DEFAULT_GUEST_NAME },
                ),
            isInGroup = true,
            fontLight = fontLight,
            horizontalPadding = horizontalPadding,
            contentMaxLines = contentMaxLines,
            onItemClick = onClickName,
        )
        IntelliMateDivider()
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.str_pronouns),
                    content = userProfile.pronouns(),
                ),
            isInGroup = true,
            fontLight = fontLight,
            horizontalPadding = horizontalPadding,
            contentMaxLines = contentMaxLines,
            onItemClick = onClickPronouns,
        )
        IntelliMateDivider()
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.chat_settings_preference_title),
                    content = preferenceContent,
                    arrow = true,
                ),
            isInGroup = true,
            fontLight = fontLight,
            horizontalPadding = horizontalPadding,
            contentMaxLines = contentMaxLines,
            onItemClick = onClickPreference,
        )
        IntelliMateDivider()
        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.str_persona),
                    content = personaContent,
                ),
            isInGroup = true,
            fontLight = fontLight,
            horizontalPadding = horizontalPadding,
            contentMaxLines = contentMaxLines,
            onItemClick = onClickPersona,
        )
    }
}

