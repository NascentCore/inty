package com.ai.intellimate.abtest

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.ai.intellimate.ui.theme.IntelliMateTheme

/**
 * AB 测试演示 Activity
 * 展示 Firebase Remote Config 的 AB 测试功能
 */
class ABTestDemoActivity : ComponentActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            IntelliMateTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    ABTestDemoScreen()
                }
            }
        }
    }
}