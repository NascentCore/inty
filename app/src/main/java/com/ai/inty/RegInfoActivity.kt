package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.screens.RegInfoScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.RegInfoActivityViewModel
import com.therouter.router.Route
import kotlinx.coroutines.launch

/**
 * 注册信息完善页面，性别和年龄
 */
@Route(path = Constant.ROUTE_REG_INFO)
class RegInfoActivity : BaseActivity() {

    private val viewModel: RegInfoActivityViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            IntyTheme {
                RegInfoContent(
                    onClose = { finish() },
                    onSave = { gender, age ->
                        viewModel.onSave(gender, age)
                    }
                )
            }
        }

        lifecycleScope.launch {
            viewModel.finishActivity.collect {
                if (it) {
                    finish()
                }
            }
        }
    }
}

/**
 * 注册信息内容组件
 */
@Composable
private fun RegInfoContent(
    onClose: () -> Unit,
    onSave: (gender: com.ai.inty.beans.GENDER, age: String) -> Unit
) {
    RegInfoScreen(
        onClose = onClose,
        onSave = onSave
    )
}
