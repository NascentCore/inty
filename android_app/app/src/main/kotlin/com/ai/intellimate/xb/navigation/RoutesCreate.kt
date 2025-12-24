package com.ai.intellimate.xb.navigation

object RoutesCreate {
    const val CreateRole = "create_role"

    const val AvatarGenerate = "avatar_generate/{initialPrompt}"


    fun avatarGenerate(initialPrompt: String) = "avatar_generate/${initialPrompt}"
}