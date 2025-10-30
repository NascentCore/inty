package com.ai.intellimate.remoteconfig

import ai.sxwl.android.common.base.BaseActivity
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier

/**
 * Firebase Remote Config AB 测试 Demo Activity
 */
class AbTestDemoActivity : BaseActivity() {
    
    private val viewModel: AbTestDemoViewModel by viewModels()
    
    override fun getPageName(): String = "AbTestDemoActivity"
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    AbTestDemoScreen(viewModel = viewModel)
                }
            }
        }
    }
}
