package com.inty.utils.env

import android.annotation.SuppressLint
import android.app.Application
import android.content.Context
import android.os.Build
import android.text.TextUtils
import com.inty.utils.AppEnv

/** @return 当前进程名 */
fun getCurrentProcessName(context: Context): String {

  // 1)通过Application的API获取当前进程名
  var currentProcessName = getCurrentProcessNameByApplication()
  if (!TextUtils.isEmpty(currentProcessName)) {
    return currentProcessName!!
  }

  // 2)通过反射ActivityThread获取当前进程名
  currentProcessName = getCurrentProcessNameByActivityThread()
  return if (!TextUtils.isEmpty(currentProcessName)) {
    currentProcessName!!
  } else {
    AppEnv.APPLICATION_ID
  }
}

fun getCurrentProcessNameByApplication(): String? {
  return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
    Application.getProcessName()
  } else null
}

/** 通过反射ActivityThread获取进程名，避免了ipc */
@SuppressLint("PrivateApi")
fun getCurrentProcessNameByActivityThread(): String? {
  var processName: String? = null
  try {
    val declaredMethod =
        Class.forName("android.app.ActivityThread", false, Application::class.java.classLoader)
            .getDeclaredMethod("currentProcessName", *arrayOfNulls<Class<*>?>(0))
    declaredMethod.isAccessible = true
    val invoke = declaredMethod.invoke(null, *arrayOfNulls(0))
    if (invoke is String) {
      processName = invoke
    }
  } catch (e: Throwable) {
    e.printStackTrace()
  }
  return processName
}
