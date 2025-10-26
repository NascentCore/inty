package ai.sxwl.android.design

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Picture
import android.os.Build
import androidx.annotation.DrawableRes
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.Interaction
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Canvas
import androidx.compose.ui.graphics.Paint
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.draw
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.semantics.Role
import androidx.core.content.ContextCompat
import androidx.core.graphics.createBitmap
import androidx.core.graphics.drawable.toBitmap
import kotlin.math.roundToInt
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow

/**
 * Modifier的扩展函数，用于捕获内部compose的UI转化为bitmap val picture = remember { Picture() }
 *
 * @param picture [Picture] 捕获的数据，存储到picture后，picture可用于转化为bitmap
 *   ⚠️注意，该功能仅能捕获对应修饰控件内的compose的ui。如果是同类的modifier扩展符号（比如appWaterMarker），就需要在该函数之后才可以
 */
fun Modifier.captureContent(picture: Picture) =
    this.drawWithCache {
        // 获取内容宽高
        val width = this.size.width.toInt()
        val height = this.size.height.toInt()
        onDrawWithContent {
            val pictureCanvas = Canvas(picture.beginRecording(width, height))
            // requires at least 1.6.0-alpha01+
            draw(this, this.layoutDirection, pictureCanvas, this.size) {
                this@onDrawWithContent.drawContent()
            }
            picture.endRecording()
            drawIntoCanvas { canvas -> canvas.nativeCanvas.drawPicture(picture) }
        }
    }

/**
 * 将picture转化为bitmap
 *
 * @param picture 是compose的Picture，需要captureContent配合使用，picture才能有内容
 */
fun createBitmapFromPicture(picture: Picture): Bitmap {
    // [START android_compose_draw_into_bitmap_convert_picture]
    val bitmap =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            Bitmap.createBitmap(picture)
        } else {
            val bitmap = createBitmap(picture.width, picture.height)
            val canvas = android.graphics.Canvas(bitmap)
            canvas.drawColor(Color.WHITE)
            canvas.drawPicture(picture)
            bitmap
        }
    // [END android_compose_draw_into_bitmap_convert_picture]
    return bitmap
}

/**
 * 通过picture来获取compose的UI添加水印后的bitmap 此时compose的UI并不会显示水印，而是会后续添加水印到bitmap中去
 *
 * @param picture 是compose的Picture，需要captureContent配合使用，picture才能有内容
 */
fun getBitmapWithAppWaterMarker(context: Context, @DrawableRes res: Int, picture: Picture): Bitmap {
    val bitmap = createBitmapFromPicture(picture)
    val size = Size(bitmap.width.toFloat(), bitmap.height.toFloat())
    // 处理 Immutable bitmap passed to Canvas constructor
    val copy = bitmap.copy(Bitmap.Config.ARGB_8888, true)
    with(Canvas(copy.asImageBitmap())) {
        appWaterMarker(context, res)?.let { bm ->
            drawImage(
                image = bm.asImageBitmap(),
                topLeftOffset = offsetOfWaterMarker(bm, size, WaterMarkerPosition.BOTTOM_END),
                paint = Paint()
            )
        }
    }
    return copy
}

// region 水印相关

/** 水印位置摆放 */
private fun offsetOfWaterMarker(
    bitmap: Bitmap,
    size: Size,
    position: WaterMarkerPosition = WaterMarkerPosition.BOTTOM_END,
) =
    when (position) {
        WaterMarkerPosition.TOP_START -> Offset.Zero
        WaterMarkerPosition.TOP_CENTER -> Offset((size.width - bitmap.width) / 2, 0f)
        WaterMarkerPosition.TOP_END -> Offset(size.width - bitmap.width, 0f)
        WaterMarkerPosition.CENTER_START ->
            Offset(
                0f,
                (size.height - bitmap.height) / 2,
            )
        WaterMarkerPosition.CENTER ->
            Offset(
                (size.width - bitmap.width) / 2,
                (size.height - bitmap.height) / 2,
            )
        WaterMarkerPosition.CENTER_END ->
            Offset(
                size.width - bitmap.width,
                (size.height - bitmap.height) / 2,
            )
        WaterMarkerPosition.BOTTOM_START ->
            Offset(
                0f,
                size.height - bitmap.height,
            )
        WaterMarkerPosition.BOTTOM_CENTER ->
            Offset(
                (size.width - bitmap.width) / 2,
                size.height - bitmap.height,
            )
        WaterMarkerPosition.BOTTOM_END ->
            Offset(
                size.width - bitmap.width,
                size.height - bitmap.height,
            )
    }

/** 水印的位置 */
enum class WaterMarkerPosition {
    TOP_START,
    TOP_CENTER,
    TOP_END,
    CENTER_START,
    CENTER,
    CENTER_END,
    BOTTOM_START,
    BOTTOM_CENTER,
    BOTTOM_END,
}

/** 项目App的图片水印,给compose的UI添加一个水印显示出来 */
fun Modifier.drawAppWaterMarker(
    context: Context,
    @DrawableRes res: Int,
    position: WaterMarkerPosition = WaterMarkerPosition.BOTTOM_END,
) =
    this.drawWithContent {
        drawContent()
        // 绘制水印
        appWaterMarker(context, res)?.let { bitmap ->
            drawImage(
                image = bitmap.asImageBitmap(),
                topLeft = offsetOfWaterMarker(bitmap, size, position)
            )
        }
    }

private fun appWaterMarker(
    context: Context,
    @DrawableRes res: Int,
    size: Size = Size.Zero,
): Bitmap? {
    // 之所以不用BitmapFactory.decodeResource 是因为该方式使用svg图片时候，就无效了。
    //  return   BitmapFactory.decodeResource(context.resources, R.drawable.icon_svg)
    val waterMarker =
        ContextCompat.getDrawable(context, res)?.let { drawable ->
            if (size != Size.Zero)
                drawable.toBitmap(
                    width = size.width.roundToInt(),
                    height = size.height.roundToInt()
                )
            else {
                drawable.toBitmap()
            }
        }
    return waterMarker
}

// endregion

// 去掉点击ripple效果的方式,可以设置给不需要ripple的button组件上，
val emptyInteractionSource =
    object : MutableInteractionSource {

        override val interactions: Flow<Interaction>
            get() = MutableSharedFlow()

        override suspend fun emit(interaction: Interaction) {}

        override fun tryEmit(interaction: Interaction) = false
    }

/** Modifier的扩展符，没有ripple点击水波纹效果 ⚠️注意，给Button等添加modifier的clickable的时候，是无效的，因为内部优先调用button自身的点击回调 */
fun Modifier.noRippleClickable(
    enabled: Boolean = true,
    onClickLabel: String? = null,
    role: Role? = null,
    onClick: () -> Unit = {},
) =
    this.composed {
        var lastClickTime by remember { mutableLongStateOf(0L) }
        clickable(
            interactionSource = emptyInteractionSource,
            indication = null,
            enabled = enabled,
            onClickLabel = onClickLabel,
            role = role,
            onClick = {
                val currentTime = System.currentTimeMillis()
                if (AntiClick.isValidClick(lastClickTime)) {
                    lastClickTime = currentTime
                    onClick()
                }
            },
        )
    }

/** 点击防抖 */
object AntiClick {
    private const val CLICK_INTERVAL = 1000L // 1 second

    fun isValidClick(lastClickTime: Long): Boolean {
        val currentTime = System.currentTimeMillis()
        return currentTime - lastClickTime >= CLICK_INTERVAL
    }
}
