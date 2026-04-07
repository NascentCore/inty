package com.ai.core.utils

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.annotation.RequiresApi
import androidx.core.content.ContextCompat

object PermissionUtils {
    fun isGranted(context: Context?, permission: String?): Boolean {
        if (context == null || permission.isNullOrEmpty()) return false
        return try {
            ContextCompat.checkSelfPermission(context, permission) ==
                PackageManager.PERMISSION_GRANTED
        } catch (e: Exception) {
            false
        }
    }

    @RequiresApi(Build.VERSION_CODES.TIRAMISU)
    fun hasNotificationPermission(context: Context?): Boolean {
        return isGranted(context, Manifest.permission.POST_NOTIFICATIONS)
    }
}
