package ai.sxwl.android.design.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.sxwl.android.design.R


@Composable
fun HeartPrimaryButton(
    btnText: String,
    enable: Boolean = true,
    onClick: () -> Unit = {},
) {

    Box(
        modifier = Modifier
            .fillMaxWidth(.95f)
            .height(50.dp)
            .clip(RoundedCornerShape(25.dp))
            .alpha(if (enable) 1f else .4f)
            .background(brush = primaryBtnBrush)
            .clickable(enabled = enable, onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = btnText,
            fontSize = 16.sp,
            lineHeight = 22.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
            textAlign = TextAlign.Center,
        )
    }
}

@Preview
@Composable
private fun 按钮效果预览() {
    Column(Modifier.background(Color.LightGray)) {
        HeartPrimaryButton("Save")
        Spacer(Modifier.height(8.dp))
        HeartPrimaryButton("Save", enable = false)

        Spacer(Modifier.height(8.dp))
        HeartFollowButton()
        Spacer(Modifier.height(8.dp))
        HeartFollowButton(isFollowing = true)

    }
}


@Composable
fun HeartFollowButton(
    isFollowing: Boolean = false,
    onClick: () -> Unit = {},
) {
    Box(
        modifier = Modifier
            .size(98.dp, 40.dp)
            .clip(RoundedCornerShape(20.dp))
            .border(width = 1.dp, brush = heartDivBrush, shape = RoundedCornerShape(20.dp))
            .background(brush = if (isFollowing) commonBtnBrush else primaryBtnBrush)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = if (isFollowing) "Following" else "Follow",
            fontSize = 14.sp,
            lineHeight = 22.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
            textAlign = TextAlign.Center,
        )
    }
}

/**
 *简单的声音播放气泡，
 * 后续再设计优化，形成反馈的反馈背景
 */
@Composable
fun VoiceBubble(modifier: Modifier = Modifier, seconds: Int = 0) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(30.dp))
            .background(Color(0XFF44354F))
            .padding(horizontal = 8.dp, vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Image(
            painter = painterResource(R.drawable.ic_voice),
            contentDescription = "",
            contentScale = ContentScale.Crop
        )
        Spacer(Modifier.width(2.dp))
        Text(
            text = "${seconds}”",
            fontSize = 14.sp,
            lineHeight = 22.sp,
            fontWeight = FontWeight.Normal,
            color = Color(0xFFF5F5F5),
        )

    }
}

@Preview
@Composable
private fun PreviewVoiceBubble() {
    VoiceBubble()
}
