package com.ai.inty.ui.components

import androidx.compose.foundation.Image
import java.util.Locale
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.billing.VipPlan

/** 会员权益项组件 */
@Composable
fun PremiumBenefitItem(text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(vertical = 2.dp),
    ) {
        Image(
            painter = painterResource(id = R.drawable.ic_checked_premium),
            contentDescription = null,
            modifier = Modifier.size(16.dp),
        )
        Spacer(Modifier.width(8.dp))
        Text(text = text, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Light)
    }
    Spacer(Modifier.height(4.dp))
}

/** 订阅计划卡片组件 */
@Composable
fun PremiumPlanCard(
    plan: VipPlan,
    isSelected: Boolean,
    isSubscribed: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val subModifier = if (isSubscribed) Modifier.alpha(.4f) else Modifier

    Box(
        modifier =
            modifier
                .fillMaxHeight()
                .background(
                    color = if (isSelected) Color(0x99350D5D) else Color(0x991C1523),
                    shape = RoundedCornerShape(8.dp),
                )
                .border(
                    width = 1.dp,
                    color = if (isSelected) Color.White else Color.Transparent,
                    shape = RoundedCornerShape(8.dp),
                )
                .then(subModifier)
                .clickable(enabled = !isSubscribed) { onClick() }
                .padding(vertical = 14.dp),
        contentAlignment = Alignment.TopCenter,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = plan.name,
                color =
                    when {
                        isSubscribed -> Color.White.copy(alpha = 0.5f)
                        else -> Color.White
                    },
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp,
                modifier = subModifier,
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = plan.price,
                color =
                    when {
                        isSubscribed -> Color.White.copy(alpha = 0.5f)
                        else -> Color.White
                    },
                fontSize = 28.sp,
                fontWeight = FontWeight.Normal,
                modifier = subModifier,
            )
        }

        // 折扣标签
        if (plan.discountRate < 1) {
            Box(
                Modifier.fillMaxWidth(0.8f)
                    .clip(RoundedCornerShape(12.dp))
                    .background(
                        brush =
                            Brush.horizontalGradient(
                                colors =
                                    listOf(Color(0xFFC1F9FD), Color(0xFFD4AEFD), Color(0xFF7B96FB))
                            )
                    )
                    .then(subModifier)
                    .align(Alignment.BottomCenter),
                contentAlignment = Alignment.Center,
            ) {
                Row(
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = String.format(Locale.getDefault(), "%d%%", kotlin.math.ceil((1-plan.discountRate) * 100).toInt()),
                        color = Color.Black,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = subModifier,
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = stringResource(R.string.discount_save),
                        color = Color.Black,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = subModifier,
                    )
                }
            }
        }
    }
}

/** 订阅计划列表组件 */
@Composable
fun PremiumPlanList(
    plans: List<VipPlan>,
    selectedIndex: Int,
    isSubscribed: Boolean,
    onPlanSelected: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.fillMaxWidth().height(132.dp).padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        plans.forEachIndexed { idx, plan ->
            PremiumPlanCard(
                plan = plan,
                isSelected = idx == selectedIndex,
                isSubscribed = isSubscribed,
                onClick = { onPlanSelected(idx) },
                modifier = Modifier.weight(1f),
            )
        }
    }
}

/** 购买按钮组件 */
@Composable
fun PurchaseButton(
    isSubscribed: Boolean,
    hasSelectedPlan: Boolean,
    onPurchase: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier =
            modifier
                .fillMaxWidth()
                .padding(horizontal = 15.dp)
                .height(56.dp)
                .clip(RoundedCornerShape(28.dp))
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors = listOf(Color(0xFF9756FF), Color(0xFFEF56FF))
                        )
                )
                .alpha(if (isSubscribed) .4f else 1f)
                .clickable(enabled = !isSubscribed && hasSelectedPlan, onClick = onPurchase),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text =
                if (isSubscribed) {
                    stringResource(R.string.premium_subscribed)
                } else {
                    stringResource(R.string.premium_subscribe)
                },
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White,
            modifier = Modifier.alpha(if (isSubscribed) .7f else 1f),
        )
    }
}

/** 自动续费提示组件 */
@Composable
fun AutoRenewalNotice(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text =
                stringResource(R.string.auto_renews_cancel) +
                    ". " +
                    stringResource(R.string.subscription_consent),
            fontSize = 12.sp,
            color = Color.White,
        )
        PolicyRow(context = LocalContext.current, fontSize = 12.sp)
    }
}

/** 空状态组件 */
@Composable
fun EmptyPlanState(modifier: Modifier = Modifier) {
    Text(
        text = stringResource(R.string.no_subscription_plans),
        color = Color.White.copy(alpha = 0.6f),
        fontSize = 14.sp,
        textAlign = TextAlign.Center,
        modifier = modifier.fillMaxWidth(),
    )
}

@Preview(showBackground = true)
@Composable
private fun PremiumBenefitItemPreview() {
    PremiumBenefitItem("无限对话次数")
}

@Preview(showBackground = true)
@Composable
private fun PurchaseButtonPreview() {
    PurchaseButton(isSubscribed = false, hasSelectedPlan = true, onPurchase = {})
}
