package com.ai.intellimate.vip

import ai.sxwl.android.design.theme.HeartColor
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController

@Composable
internal fun SubsManagementScreen(
    navController: NavController,
    viewModel: SubsManageViewModel = viewModel()
) {
    SubscriptionManagementScreen(
        navController,
        modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor),
        viewModel = viewModel,
    )
}