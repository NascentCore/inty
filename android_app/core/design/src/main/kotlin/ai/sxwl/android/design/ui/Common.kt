package ai.sxwl.android.design.ui

import ai.sxwl.android.design.R
import ai.sxwl.android.design.theme.HeartColor
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SwipeToDismissBox
import androidx.compose.material3.SwipeToDismissBoxValue
import androidx.compose.material3.Text
import androidx.compose.material3.rememberSwipeToDismissBoxState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.random.Random

// 存放一些普通的ui相关的函数

/** 简单的扩展函数，用于对数值标记为0 和 1 的时候;如果是null，则默认为0 数值取反 作为类似boolean的效果 */
fun Int.not(): Int {

    assert(this == 1 || this == 0)

    return when (this) {
        0 -> 1
        1 -> 0
        else -> error("")
    }
}

// 主题按钮 渐变色
val primaryBtnBrush =
    Brush.horizontalGradient(colors = listOf(Color(0xFFC122FF), Color(0xFFFF905D)))

// 常规按钮 渐变色
val commonBtnBrush = Brush.horizontalGradient(colors = listOf(Color(0XFF2D213A), Color(0XFF2D213A)))

// 分隔符渐变色
val heartDivBrush =
    Brush.horizontalGradient(
        colors = listOf(Color.White.copy(0f), Color.White.copy(.09f), Color.White.copy(0f))
    )

/** 空状态页面 */
@Preview
@Composable
fun HeartEmptyUI(modifier: Modifier = Modifier, tips: String = "No relevant content") {
    Column(
        modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Image(
            painter = painterResource(R.drawable.img_empty_content),
            contentDescription = "",
            contentScale = ContentScale.Crop,
            modifier = Modifier,
        )
        Text(
            text = tips,
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            color = Color(0x8CFFFFFF),
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
fun PoundTagText(textStr: String) {
    Box(
        modifier =
            Modifier.border(
                    width = 1.dp,
                    brush = heartDivBrush,
                    shape = RoundedCornerShape(size = 4.dp),
                )
                .background(
                    color = HeartColor.primaryColor,
                    shape = RoundedCornerShape(size = 4.dp),
                )
                .padding(horizontal = 6.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = textStr,
            fontSize = 12.sp,
            fontWeight = FontWeight.Light,
            color = Color(0x8CFFFFFF),
            textAlign = TextAlign.Center,
        )
    }
}

@Preview
@Composable
private fun PreviewPoundText() {
    Row {
        PoundTagText("#Female")
        PoundTagText("#Mmale")
    }
}
