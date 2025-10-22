package ai.sxwl.android.utils

import android.Manifest
import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.annotation.RequiresPermission

/**
 * 震动工具类
 * 提供震动相关的工具方法
 */
object VibrateUtils {

    /**
     * 震动
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(duration: Long) {
        vibrate(Utils.getApp(), duration)
    }

    /**
     * 震动
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(context: Context?, duration: Long) {
        if (context == null) return
        val vibrator = getVibrator(context)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(
                VibrationEffect.createOneShot(
                    duration,
                    VibrationEffect.DEFAULT_AMPLITUDE
                )
            )
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(duration)
        }
    }

    /**
     * 震动
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(pattern: LongArray, repeat: Int) {
        vibrate(Utils.getApp(), pattern, repeat)
    }

    /**
     * 震动
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(context: Context?, pattern: LongArray, repeat: Int) {
        if (context == null) return
        val vibrator = getVibrator(context)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createWaveform(pattern, repeat))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(pattern, repeat)
        }
    }

    /**
     * 取消震动
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun cancel() {
        cancel(Utils.getApp())
    }

    /**
     * 取消震动
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun cancel(context: Context?) {
        if (context == null) return
        val vibrator = getVibrator(context)
        vibrator.cancel()
    }

    /**
     * 获取Vibrator
     */
    private fun getVibrator(context: Context): Vibrator {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager =
                context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vibratorManager.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
    }

    /**
     * 是否有震动器
     */
    fun hasVibrator(): Boolean {
        return hasVibrator(Utils.getApp())
    }

    /**
     * 是否有震动器
     */
    fun hasVibrator(context: Context?): Boolean {
        if (context == null) return false
        val vibrator = getVibrator(context)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.hasVibrator()
        } else {
            @Suppress("DEPRECATION")
            vibrator.hasVibrator()
        }
    }
}
