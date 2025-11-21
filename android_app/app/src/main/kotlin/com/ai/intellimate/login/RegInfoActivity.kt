package com.ai.intellimate.login

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.GENDER
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.PermissionUtils
import android.Manifest
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import com.ai.intellimate.ViewModelEvent

/** 注册信息完善页面，性别和年龄 */
class RegInfoActivity : BaseActivity() {

    companion object {
        /**
         * 启动注册信息页面
         *
         * @param context 上下文context
         */
        fun launch(context: Context) {
            context.startActivity(Intent(context, RegInfoActivity::class.java))
        }
    }

    private val viewModel: RegInfoViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        // 事件监听在 Compose UI 中处理
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()

        // 通知权限申请 Launcher（Android 13+）
        val notificationPermissionLauncher =
            rememberLauncherForActivityResult(
                contract = ActivityResultContracts.RequestPermission()
            ) { isGranted ->
                if (isGranted) {
                    LogUtils.i("RegInfoActivity", "通知权限已授予")
                } else {
                    LogUtils.w("RegInfoActivity", "通知权限被拒绝")
                }
                // 无论权限是否授予，都关闭页面
                finish()
            }

        // 监听 ViewModel 事件，在用户信息更新成功后申请通知权限
        LaunchedEffect(Unit) {
            viewModel.events.collect { event ->
                when (event) {
                    is ViewModelEvent.UserProfileUpdated -> {
                        // 用户信息更新成功，申请通知权限（Android 13+）
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            if (!PermissionUtils.hasNotificationPermission(this@RegInfoActivity)) {
                                // 申请通知权限
                                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                            } else {
                                // 已有权限，直接关闭页面
                                finish()
                            }
                        } else {
                            // Android 13 以下不需要申请，直接关闭页面
                            finish()
                        }
                    }
                    else -> {
                        // 其他事件暂不处理
                    }
                }
            }
        }

        RegInfoContent(
            onClose = { finish() },
            onSave = { gender, age -> viewModel.onSave(gender, age) },
        )
    }
}

/** 注册信息内容组件 */
@Composable
private fun RegInfoContent(onClose: () -> Unit, onSave: (gender: GENDER, age: String) -> Unit) {
    RegInfoScreen(onClose = onClose, onSave = onSave)
}
