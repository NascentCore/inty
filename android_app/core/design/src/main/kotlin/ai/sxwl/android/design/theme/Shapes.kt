package ai.sxwl.android.design.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ShapeDefaults
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

/**
 * 定义一些项目内常用的形状，便于统一管理
 */
internal val heartShapes = Shapes(
    extraSmall = ShapeDefaults.ExtraSmall,
    small = ShapeDefaults.Small,
    medium = ShapeDefaults.Medium,
    large = ShapeDefaults.Large,
    extraLarge = ShapeDefaults.ExtraLarge
)

/**
 * 封装一些用户整个项目配置的shape的圆角，便于统一
 */
object HeartCornerShapes {
    val extraSmall = RoundedCornerShape(2.dp)
    val small = RoundedCornerShape(4.dp)
    val medium = RoundedCornerShape(8.dp)
    val large = RoundedCornerShape(12.dp)
    val extraLarge = RoundedCornerShape(16.dp)
}
