package ai.sxwl.android.design.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun BlurBgCard(
    modifier: Modifier = Modifier,
    contentAlignment: Alignment = Alignment.Center,
    content: @Composable BoxScope.() -> Unit,
) {

    Box(modifier = modifier, contentAlignment) {

        // 横向渐变边框（左右边缘向内渐变）
        Box(
            modifier =
                Modifier.matchParentSize()
                    .background(
                        brush =
                            Brush.horizontalGradient(
                                colors =
                                    listOf(
                                        Color.White.copy(0.1f),
                                        Color.Transparent,
                                        Color.Transparent,
                                        Color.Transparent,
                                        Color.Transparent,
                                        Color.Transparent,
                                        Color.White.copy(0.1f),
                                    )
                            ),
                        shape = RoundedCornerShape(8.dp),
                    )
        )

        // 纵向渐变边框（上下边缘向内渐变）
        Box(
            modifier =
                Modifier.matchParentSize()
                    .background(
                        brush =
                            Brush.verticalGradient(
                                colors =
                                    listOf(
                                        Color.White.copy(0.1f),
                                        Color.Transparent,
                                        Color.Transparent,
                                        Color.Transparent,
                                        Color.Transparent,
                                        Color.White.copy(0.1f),
                                    )
                            ),
                        shape = RoundedCornerShape(8.dp),
                    )
        )

        // content
        content()
    }
}

@Preview
@Composable
private fun PreviewBlurBgCard() {
    BlurBgCard(modifier = Modifier.fillMaxWidth().height(200.dp)) { Text("哈哈哈哈") }
}
