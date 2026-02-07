package com.ai.intellimate.login

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.PermissionUtils
import ai.sxwl.android.utils.findActivity
import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import com.ai.intellimate.ui.components.PermissionSettingsDialog

@Composable
internal fun RegInfoPage(navController: NavController, viewModel: RegInfoViewModel = viewModel()) {
    val context = LocalContext.current
    val activity = context.findActivity()
    var hasRequestedNotificationPermission by rememberSaveable { mutableStateOf(false) }
    var showNotificationSettingsDialog by rememberSaveable { mutableStateOf(false) }
    // 通知权限申请 Launcher（Android 13+）
    val notificationPermissionLauncher =
        rememberLauncherForActivityResult(contract = ActivityResultContracts.RequestPermission()) {
            isGranted ->
            if (isGranted) {
                LogUtils.i("RegInfoActivity", "通知权限已授予")
                navController.popBackStack()
            } else {
                LogUtils.w("RegInfoActivity", "通知权限被拒绝")
                val isPermanentlyDenied =
                    PermissionUtils.isPermissionPermanentlyDenied(
                        activity,
                        Manifest.permission.POST_NOTIFICATIONS,
                        hasRequestedNotificationPermission,
                    )
                if (isPermanentlyDenied) {
                    showNotificationSettingsDialog = true
                } else {
                    navController.popBackStack()
                }
            }
        }

    // 监听 ViewModel 事件，在用户信息更新成功后申请通知权限
    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is ViewModelEvent.UserProfileUpdated -> {
                    // 用户信息更新成功，申请通知权限（Android 13+）
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        if (!PermissionUtils.hasNotificationPermission(context)) {
                            // 申请通知权限
                            hasRequestedNotificationPermission = true
                            notificationPermissionLauncher.launch(
                                Manifest.permission.POST_NOTIFICATIONS
                            )
                        } else {
                            // 已有权限，直接关闭页面
                            navController.popBackStack()
                        }
                    } else {
                        // Android 13 以下不需要申请，直接关闭页面
                        navController.popBackStack()
                    }
                }
                else -> {
                    // 其他事件暂不处理
                }
            }
        }
    }

    if (showNotificationSettingsDialog) {
        PermissionSettingsDialog(
            title = stringResource(R.string.permission_settings_title),
            description = stringResource(R.string.permission_settings_notification_description),
            confirmText = stringResource(R.string.permission_settings_open_settings),
            cancelText = stringResource(R.string.cancel),
            onConfirm = {
                showNotificationSettingsDialog = false
                PermissionUtils.openAppPermissionSettings(context)
                navController.popBackStack()
            },
            onDismiss = {
                showNotificationSettingsDialog = false
                navController.popBackStack()
            },
        )
    }

    RegInfoScreen(
        onClose = { navController.popBackStack() },
        onSave = { gender, age -> viewModel.onSave(gender, age) },
    )
}
