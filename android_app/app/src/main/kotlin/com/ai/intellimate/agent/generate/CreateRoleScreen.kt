package com.ai.intellimate.agent.generate

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController

@Composable
internal fun CreateRoleScreen(
    navController: NavController,
    createRoleViewModel: CreateRoleViewModel = viewModel(),
    agentInfo: AgentInfo? = null,
    draftId: String? = null,
) {
    CreateRolePage(
        navController,
        modifier = Modifier.fillMaxSize(),
        createRoleViewModel = createRoleViewModel,
        onCreateSuccess = {
            //            setResult(Activity.RESULT_OK)
            //            finish()
        },
        onAvatarGenerateClick = { prompt ->
            //            AvatarGenerateActivity.launch(this, prompt?.takeIf { it.isNotBlank() })
        },
        onBack = {},
        editAgent = agentInfo,
        draftId = draftId,
    )
}
