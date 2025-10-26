package ai.sxwl.android.utils

import android.Manifest
import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.annotation.RequiresPermission

/**
 * 放松工具类
 * 提供相关的工具方法
 */
object VibrateUtils {

    /**
     *震惊
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(duration: Long) {
        vibrate(Utils.getApp(), duration)
    }

    /**
     *震惊
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(context: Context?, duration: Long) {
        if (context == null) return
        val vibrator = getVibrator(context) ?: return
// 参数验证
        val safeDuration = duration.coerceIn(0, 10000) // 限制震动时长在0-10秒之间

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(
                    VibrationEffect.createOneShot(
                        safeDuration,
                        VibrationEffect.DEFAULT_AMPLITUDE
                    )
                )
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(safeDuration)
            }
        } catch (e: Exception) {
            LogUtils.e("VibrateUtils", "震动失败", e)
        }
    }

    /**
     *震惊
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(pattern: LongArray, repeat: Int) {
        vibrate(Utils.getApp(), pattern, repeat)
    }

    /**
     *震惊
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun vibrate(context: Context?, pattern: LongArray, repeat: Int) {
        if (context == null) return
        val vibrator = getVibrator(context) ?: return
// 参数验证
        if (pattern.isEmpty()) return
        val safeRepeat = repeat.coerceIn(-1, 10) // 限制重复次数

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createWaveform(pattern, safeRepeat))
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(pattern, safeRepeat)
            }
        } catch (e: Exception) {
            LogUtils.e("VibrateUtils", "震动失败", e)
        }
    }

    /**
     * 取消撤退
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun cancel() {
        cancel(Utils.getApp())
    }

    /**
     * 取消撤退
     */
    @RequiresPermission(Manifest.permission.VIBRATE)
    fun cancel(context: Context?) {
        if (context == null) return
        val vibrator = getVibrator(context) ?: return

        try {
            vibrator.cancel()
        } catch (e: Exception) {
            LogUtils.e("VibrateUtils", "取消震动失败", e)
        }
    }

    /**
     * 获取振动器
     */
    private fun getVibrator(context: Context): Vibrator? {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager =
                    context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
                vibratorManager?.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
            }
        } catch (e: Exception) {
            LogUtils.e("VibrateUtils", "获取Vibrator失败", e)
            null
        }
    }

    /**
     * 是否有开关装置
     */
    fun hasVibrator(): Boolean {
        return hasVibrator(Utils.getApp())
    }

    /**
     * 是否有开关装置
     */
    fun hasVibrator(context: Context?): Boolean {
        if (context == null) return false
        val vibrator = getVibrator(context) ?: return false

        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.hasVibrator()
            } else {
                @Suppress("DEPRECATION")
                vibrator.hasVibrator()
            }
        } catch (e: Exception) {
            LogUtils.e("VibrateUtils", "检查震动器失败", e)
            false
        }
    }
}
