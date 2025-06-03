package com.inty.utils

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.provider.Settings
import com.inty.utils.env.getCurrentProcessName
import com.inty.utils.storage.IntySetting
import java.io.File
import java.lang.ref.WeakReference
import java.util.Locale

@SuppressLint("StaticFieldLeak")
object AppEnv {
    private const val DEFAULT_CHANNEL = "offical"

    var topActivity: WeakReference<Activity>? = null

    lateinit var context: Context
    var testEnv = false
    var DEBUG = false
    var APPLICATION_ID = ""
    var version_name = "0.0"
    var version_code: Int = 0

    val dirs by lazy {
        DirsEnv()
    }

    val processName by lazy {
        getCurrentProcessName(context)
    }

    val locale by lazy {
        Locale.getDefault()
    }
    val isZh by lazy {
        (locale.language == "zh")
    }

    val DeviceID: String by lazy {
        var id = IntySetting.getDeviceID()
        if (id.isNullOrEmpty()) {
            id = Settings.Secure.getString(
                context.getContentResolver(), Settings.Secure.ANDROID_ID
            )
            IntySetting.setDeviceID(id)
        }
        id ?: ""
    }
}

class DirsEnv {
    companion object {
        const val TAG = "DirsEnv"
    }
    val rootDir: File by lazy {
        val tmp = AppEnv.context.getExternalFilesDir("ata")!!
        tmp.mkdirs()
        tmp
    }
    val root: String by lazy {
        rootDir.absolutePath
    }
    val imagecache: String by lazy {
        makeDir("imagecache")
    }

    val logDir: String by lazy {
        makeDir("logs")
    }

    val audioInput: String by lazy {
        makeDir("audio_input")
    }

    val audioCache: String by lazy {
        makeDir("audio_cache")
    }

    val download: String by lazy {
        makeDir("download")
    }

    fun makeDir(dirName: String): String {
        val dir = File(rootDir, dirName)
        dir.mkdirs()

        return dir.absolutePath
    }
}

