package ai.sxwl.android.utils

import android.Manifest
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.annotation.RequiresApi
import androidx.core.app.ActivityCompat
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

    fun shouldShowPermissionRationale(activity: Activity?, permission: String): Boolean {
        if (activity == null || permission.isBlank()) return false
        return ActivityCompat.shouldShowRequestPermissionRationale(activity, permission)
    }

    fun isPermissionPermanentlyDenied(
        activity: Activity?,
        permission: String,
        hasRequested: Boolean,
    ): Boolean {
        if (!hasRequested) return false
        if (activity == null || permission.isBlank()) return false
        if (isGranted(activity, permission)) return false
        return !shouldShowPermissionRationale(activity, permission)
    }

    fun openAppPermissionSettings(
        context: Context,
        packageName: String = context.packageName,
    ): Boolean {
        if (packageName.isBlank()) return false
        val intent =
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        return try {
            context.startActivity(intent)
            true
        } catch (e: ActivityNotFoundException) {
            false
        } catch (e: SecurityException) {
            false
        }
    }
}

fun Context.findActivity(): Activity? =
    when (this) {
        is Activity -> this
        is ContextWrapper -> baseContext.findActivity()
        else -> null
    }
