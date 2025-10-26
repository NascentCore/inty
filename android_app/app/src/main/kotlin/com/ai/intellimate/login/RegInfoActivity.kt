package com.ai.intellimate.login

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.GENDER
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.lifecycle.lifecycleScope
import com.ai.intellimate.ViewModelEvent
import kotlinx.coroutines.launch

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
        // 监听ViewModel事件
        lifecycleScope.launch {
            viewModel.events.collect { event ->
                when (event) {
                    is ViewModelEvent.UserProfileUpdated -> {
                        finish()
                    }
                    else -> {
                        // 其他事件暂不处理
                    }
                }
            }
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        RegInfoContent(
            onClose = { finish() },
            onSave = { gender, age -> viewModel.onSave(gender, age) },
        )
    }
}

/** 注册信息内容组件 */
@Composable
private fun RegInfoContent(
    onClose: () -> Unit,
    onSave: (gender: GENDER, age: String) -> Unit,
) {
    RegInfoScreen(onClose = onClose, onSave = onSave)
}
