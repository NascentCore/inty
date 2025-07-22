package com.ai.inty.utils

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.net.Uri
import androidx.core.graphics.toColorInt
import com.inty.utils.AppEnv
import com.yalantis.ucrop.UCrop
import com.yalantis.ucrop.UCropActivity
import java.io.File

object UCropHelper {

    fun getIntent(context: Context, srcUri: Uri, title: String): Intent {


        val avatarTempFile = File(AppEnv.dirs.imagecache, "tmp.jpg")
        val uCropOptions = UCrop.Options()
        uCropOptions.apply {
            setCompressionFormat(Bitmap.CompressFormat.JPEG)
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

        val intentCrop = UCrop.of(srcUri, Uri.fromFile(avatarTempFile))
            .withAspectRatio(1f, 1f)
            .withOptions(uCropOptions)
            .withMaxResultSize(1080, 1080)
            .getIntent(context)

        return intentCrop
    }
}