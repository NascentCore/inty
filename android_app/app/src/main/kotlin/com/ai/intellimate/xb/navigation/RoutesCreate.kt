package com.ai.intellimate.xb.navigation

import io.ktor.http.encodeURLPath

object RoutesCreate {
    const val CreateRole = "create_role/{draftId}"

    const val AvatarGenerate = "avatar_generate/{initialPrompt}"

    fun createRole(draftId: String) = "create_role/${draftId}"

    fun avatarGenerate(initialPrompt: String) = "avatar_generate/${initialPrompt.encodeURLPath(true)}"
}
