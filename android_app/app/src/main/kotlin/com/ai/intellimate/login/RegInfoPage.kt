package com.ai.intellimate.login

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.PermissionUtils
import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.ViewModelEvent

@Composable
internal fun RegInfoPage(navController: NavController, viewModel: RegInfoViewModel = viewModel()) {
    // 通知权限申请 Launcher（Android 13+）
    val notificationPermissionLauncher =
        rememberLauncherForActivityResult(contract = ActivityResultContracts.RequestPermission()) {
            isGranted ->
            if (isGranted) {
                LogUtils.i("RegInfoActivity", "通知权限已授予")
            } else {
                LogUtils.w("RegInfoActivity", "通知权限被拒绝")
            }
            // 无论权限是否授予，都关闭页面
            //            finish()
            navController.popBackStack()
        }

    // 监听 ViewModel 事件，在用户信息更新成功后申请通知权限
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        viewModel.events.collect { event ->
            when (event) {
                is ViewModelEvent.UserProfileUpdated -> {
                    // 用户信息更新成功，申请通知权限（Android 13+）
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        if (!PermissionUtils.hasNotificationPermission(context)) {
                            // 申请通知权限
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

    RegInfoScreen(
        onClose = { navController.popBackStack() },
        onSave = { gender, age, mbti -> viewModel.onSave(gender, age, mbti) },
    )
}
