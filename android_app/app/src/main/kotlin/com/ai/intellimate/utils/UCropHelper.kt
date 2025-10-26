package com.ai.intellimate.utils

import ai.sxwl.android.utils.PathUtils
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.net.Uri
import androidx.core.graphics.toColorInt
import com.yalantis.ucrop.UCrop
import com.yalantis.ucrop.UCropActivity
import java.io.File

object UCropHelper {
    fun getIntent(context: Context, srcUri: Uri, title: String): Intent {
// 使用计时器创建唯一的文件名并避免缓存冲突
        val timestamp = System.currentTimeMillis()
// 这是必需的，否则 preview 将始终为 tmp。.jpg
// 这样第一次修改后就可以查看preview了，
//但未来的更新将永远是陈旧的。
        val avatarTempFile = File(PathUtils.getExternalAppCachePath(), "my_avatar_${timestamp}.jpg")

        val uCropOptions = UCrop.Options()
        uCropOptions.apply {
            setCompressionFormat(Bitmap.CompressFormat.JPEG)
// 根据投影，2048在质量和大小之间取得了很好的平衡。
            setMaxBitmapSize(2048)
// 将 compression 质量设置为 80 以更好地控制文件大小
            setCompressionQuality(80)
            setCircleDimmedLayer(true)
            setAllowedGestures(UCropActivity.SCALE, UCropActivity.NONE, UCropActivity.NONE)
            setHideBottomControls(true)
            setToolbarTitle(title)
            setToolbarColor("#1C1523".toColorInt())
            setToolbarWidgetColor(Color.WHITE)
            setShowCropFrame(false)
            setShowCropGrid(false)
            setFreeStyleCropEnabled(false)
        }

        val intentCrop =
            UCrop.of(srcUri, Uri.fromFile(avatarTempFile))
                .withAspectRatio(1f, 1f)
                .withOptions(uCropOptions)
                .withMaxResultSize(1080, 1080)
                .getIntent(context)

        return intentCrop
    }
}
