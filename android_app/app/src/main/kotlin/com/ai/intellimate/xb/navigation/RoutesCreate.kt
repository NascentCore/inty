package com.ai.intellimate.xb.navigation

import io.ktor.http.encodeURLPath

object RoutesCreate {
    const val CreateRole = "create_role/{draftId}?agentId={agentId}"

    const val AvatarGenerate = "avatar_generate/{initialPrompt}"

    fun createRole(draftId: String, agentId: String = "") =
        "create_role/${draftId}?agentId=${agentId.encodeURLPath(true)}"

    fun avatarGenerate(initialPrompt: String) =
        "avatar_generate/${initialPrompt.encodeURLPath(true)}"
}
