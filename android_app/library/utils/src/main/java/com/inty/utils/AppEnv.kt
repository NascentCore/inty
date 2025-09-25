package com.inty.utils

import android.annotation.SuppressLint
import android.content.Context
import android.provider.Settings
import com.inty.utils.env.getCurrentProcessName
import com.inty.utils.storage.IntySetting
import java.io.File
import java.util.Locale

@SuppressLint("StaticFieldLeak")
object AppEnv {

  lateinit var context: Context

  // Build types are defined in build.gradle.kts.
  var buildType: String = "debug"
  var testEnv = false
  var DEBUG = false
  var APPLICATION_ID = ""
  var version_name = "0.0"
  var version_code: Int = 0

  val dirs by lazy { DirsEnv() }

  val processName by lazy { getCurrentProcessName(context) }

  val locale by lazy { Locale.getDefault() }

  val DeviceID: String by lazy {
    var id = IntySetting.getDeviceID()
    if (id.isNullOrEmpty()) {
      id = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
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
  val root: String by lazy { rootDir.absolutePath }
  val imagecache: String by lazy { makeDir("imagecache") }

  val logDir: String by lazy { makeDir("logs") }

  fun makeDir(dirName: String): String {
    val dir = File(rootDir, dirName)
    dir.mkdirs()

    return dir.absolutePath
  }
}
