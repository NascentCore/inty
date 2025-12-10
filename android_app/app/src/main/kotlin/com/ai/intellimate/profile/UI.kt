package com.ai.intellimate.profile

import ai.sxwl.android.data.billing.VipStatus
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.AntiClick
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.BiasAlignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs


/** Premium Banner 组件 */
@Composable
internal fun PremiumBanner(
    status: String? = "Activate Now",
    purchaseTime: String? = null, // 购买日期
    expireTime: String? = null, // 过期时间
    onClick: () -> Unit = {},
) {
    var lastClickTimePremium by remember { mutableLongStateOf(0L) }

    // 使用 fillMaxWidth 适配屏幕宽度（不含padding），高度保持 120.dp
    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .clip(RoundedCornerShape(8.dp))
                .height(UiConfigs.MePage.VipBannerHeight)
                .clickable {
                    val currentTime = System.currentTimeMillis()
                    if (AntiClick.isValidClick(lastClickTimePremium)) {
                        lastClickTimePremium = currentTime
                        if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                            onClick()
                        }
                    }
                }
    ) {
        // 使用 FillBounds 填充整个区域，适配屏幕宽度
        Image(
            painter = painterResource(R.drawable.img_vip_banner),
            contentDescription = "",
            contentScale = ContentScale.Crop,
            modifier = Modifier.matchParentSize(),
        )

        Row(
            Modifier
                .border(
                    width = 0.5.dp,
                    color = Color(0x61D523FF),
                    shape = RoundedCornerShape(size = UiConfigs.MePage.AgentCardCornerRadius),
                )
                .background(
                    color = Color(0x33D216FF),
                    shape = RoundedCornerShape(size = UiConfigs.MePage.AgentCardCornerRadius),
                )
                .padding(horizontal = UiConfigs.MePage.TopIconsRow.Spacing)
                .align(BiasAlignment(.95f, .1f)),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
        ) {
            // 三种UI状态显示，1. 无有效订阅 显示Activate Now；2. 有效订阅 显示Since 日期；3. 有订阅快过期 显示Expires ON 日期
            val str =
                when (status) {
                    VipStatus.UI_SUBSCRIBED -> "Since $purchaseTime"
                    VipStatus.UI_SUBSCRIBED_EXPIRE_SOON -> "Expires on $expireTime"
                    else -> "Activate now"
                }

            Text(text = str, fontSize = 16.sp, color = Color.White, textAlign = TextAlign.Center)
        }
    }
}


@Preview
@Composable
private fun PreviewPremiumBanner() {
    PremiumBanner()
}
