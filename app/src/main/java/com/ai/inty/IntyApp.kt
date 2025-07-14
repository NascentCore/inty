package com.ai.inty

import android.app.Application
import android.content.Context
import com.ai.inty.base.initImageLoader
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.log.defaultInit
import com.therouter.TheRouter

/**
 * 应用Application的实现类
 */
class IntyApp : Application() {


    override fun attachBaseContext(base: Context?) {
        AppEnv.context = this
        AppEnv.DEBUG = BuildConfig.DEBUG
        AppEnv.testEnv = BuildConfig.DEBUG
        AppEnv.version_code = BuildConfig.VERSION_CODE
        AppEnv.version_name = BuildConfig.VERSION_NAME
        AppEnv.APPLICATION_ID = BuildConfig.APPLICATION_ID


        TheRouter.isDebug = BuildConfig.DEBUG

        super.attachBaseContext(base)
    }

    override fun onCreate() {
        super.onCreate()

        EasyLog.defaultInit()
        initImageLoader()
    }
}