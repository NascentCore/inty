package com.ai.inty

import android.app.Application
import android.content.Context
import com.inty.utils.AppEnv
import com.therouter.TheRouter

class IntyApp : Application() {


    override fun attachBaseContext(base: Context?) {
        AppEnv.context = this
        TheRouter.isDebug = true
        super.attachBaseContext(base)
    }

    override fun onCreate() {
        super.onCreate()
    }
}