package com.ai.intellimate.demo

import ai.sxwl.android.common.base.BaseActivity
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier

/**
 * Firebase Remote Config AB 测试演示 Activity
 *
 * 使用方法：
 * 1. 在 AndroidManifest.xml 中注册此 Activity
 * 2. 通过 Intent 启动此 Activity 查看演示
 *
 * 示例代码：
 * ```kotlin
 * val intent = Intent(context, RemoteConfigAbTestActivity::class.java)
 * context.startActivity(intent)
 * ```
 */
class RemoteConfigAbTestActivity : BaseActivity() {

    override fun getPageName(): String = "RemoteConfigAbTestActivity"

    @androidx.compose.runtime.Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        RemoteConfigAbTestDemo(
            modifier = Modifier.fillMaxSize()
        )
    }
}