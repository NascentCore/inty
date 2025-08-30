package com.ai.inty.base

import android.content.Context
import android.content.res.Configuration
import android.os.Bundle
import android.os.PersistableBundle
import androidx.activity.ComponentActivity
import com.therouter.TheRouter

open class BaseActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        onInit()
    }

    private fun onInit() {
        TheRouter.inject(this)
    }

    override fun attachBaseContext(newBase: Context) {
        val overrideConfiguration = Configuration(newBase.resources.configuration)
        overrideConfiguration.fontScale = 1.0f
        super.attachBaseContext(newBase.createConfigurationContext(overrideConfiguration))
    }

    override fun onCreate(savedInstanceState: Bundle?, persistentState: PersistableBundle?) {
        super.onCreate(savedInstanceState, persistentState)
        onInit()
    }
}
