package com.ai.intellimate.ui.components

import ai.sxwl.android.data.billing.VipPlan
import ai.sxwl.android.design.theme.IntelliMateTheme
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import java.util.Locale
import kotlin.math.ceil

/** 折扣标签组件，使用 MaterialTheme 颜色与字体。 */
@Composable
private fun DiscountTag(discountRate: Double, modifier: Modifier = Modifier) {
    val colorScheme = MaterialTheme.colorScheme
    val typography = MaterialTheme.typography
    val shapes = MaterialTheme.shapes
    Box(
        modifier =
            modifier
                .fillMaxWidth(0.6f)
                .clip(shapes.medium)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors =
                                listOf(
                                    colorScheme.tertiary,
                                    colorScheme.secondary,
                                    colorScheme.primary,
                                )
                        )
                ),
        contentAlignment = Alignment.Center,
    ) {
        Row(
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text =
                    String.format(
                        Locale.getDefault(),
                        "%d%%",
                        ceil((1 - discountRate) * 100).toInt(),
                    ),
                style = typography.labelLarge,
                color = colorScheme.onPrimary,
            )
            Spacer(modifier = Modifier.width(2.dp))
            Text(
                text = stringResource(R.string.discount_save),
                style = typography.labelLarge,
                color = colorScheme.onPrimary,
            )
        }
    }
}

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

/** 订阅计划卡片组件，使用 MaterialTheme 颜色、字体与形状。 */
@Composable
fun PremiumPlanCard(
    plan: VipPlan,
    isSelected: Boolean,
    isSubscribed: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colorScheme = MaterialTheme.colorScheme
    val typography = MaterialTheme.typography
    val shapes = MaterialTheme.shapes
    val subModifier = if (isSubscribed) Modifier.alpha(.4f) else Modifier
    val cardBg =
        if (isSelected)
            Brush.verticalGradient(
                listOf(
                    colorScheme.tertiary,
                    colorScheme.secondary,
                    colorScheme.primary,
                )
            )
        else
            Brush.verticalGradient(
                listOf(
                    colorScheme.surface.copy(alpha = 0.5f),
                    colorScheme.surface.copy(alpha = 0.5f),
                )
            )
    val innerBg = if (isSelected) colorScheme.surface else Color.Transparent
    val textColor =
        when {
            isSubscribed -> colorScheme.onBackground.copy(alpha = 0.5f)
            else -> colorScheme.onBackground
        }

    Box(
        modifier =
            modifier
                .fillMaxHeight()
                .then(subModifier)
                .clickable(enabled = !isSubscribed) {
                    onClick()
                },
        contentAlignment = Alignment.TopCenter,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Spacer(modifier = Modifier.height(15.dp))

            Box(
                modifier
                    .width(110.dp)
                    .height(97.dp)
                    .background(brush = cardBg, shape = shapes.small)
                    .padding(1.dp)
            ) {
                Box(
                    modifier =
                        Modifier
                            .matchParentSize()
                            .background(innerBg, shape = shapes.small)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 4.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = plan.name,
                            style = typography.labelLarge,
                            color = textColor,
                            modifier = subModifier,
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Box(
                            modifier =
                                Modifier
                                    .fillMaxWidth()
                                    .height(1.dp)
                                    .background(colorScheme.outline.copy(alpha = 0.4f))
                        )
                        val displayPrice = remember(plan.price) { plan.price.replace(".00", "") }
                        val priceStyle =
                            remember(displayPrice, typography) {
                                val priceLength =
                                    displayPrice
                                        .filter { it.isDigit() || it == '.' || it == ',' }
                                        .length
                                when {
                                    priceLength <= 3 -> typography.titleMedium
                                    priceLength <= 5 -> typography.titleSmall
                                    priceLength <= 7 -> typography.bodyLarge
                                    else -> typography.labelLarge
                                }
                            }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = displayPrice,
                            style = priceStyle,
                            color = textColor,
                            modifier = subModifier,
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))
        }

        // 折扣标签
        if (plan.discountRate < 1) {
            DiscountTag(
                discountRate = plan.discountRate,
                modifier = Modifier
                    .then(subModifier)
                    .align(Alignment.TopEnd),
            )
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
        modifier = modifier
            .fillMaxWidth()
            .height(122.dp)
            .padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
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

/**
 * 购买按钮组件，使用 MaterialTheme 颜色、字体与形状。
 * 当 [selectedPlanPrice] 非空且未订阅时，按钮文案为「价格 Get Premium」；否则为「Subscribe」/「Subscribed」。
 */
@Composable
fun PurchaseButton(
    isSubscribed: Boolean,
    hasSelectedPlan: Boolean,
    onPurchase: () -> Unit,
    modifier: Modifier = Modifier,
    isLoading: Boolean = false,
    selectedPlanPrice: String? = null,
) {
    val colorScheme = MaterialTheme.colorScheme
    val typography = MaterialTheme.typography
    val shapes = MaterialTheme.shapes
    val buttonText =
        when {
            isSubscribed -> stringResource(R.string.premium_subscribed)
            !selectedPlanPrice.isNullOrBlank() ->
                stringResource(R.string.subscription_btn_price_get_premium, selectedPlanPrice)
            else -> stringResource(R.string.premium_subscribe)
        }
    Box(
        modifier =
            modifier
                .fillMaxWidth()
                .height(56.dp)
                .alpha(if (isSubscribed) 0.6f else 1f)
                .clickable(
                    enabled = !isSubscribed && hasSelectedPlan && !isLoading,
                    onClick = onPurchase,
                ),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            shape = RoundedCornerShape(100),
            color = colorScheme.secondaryContainer,
            modifier = Modifier.fillMaxSize(),
        ) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        color = colorScheme.onPrimary,
                        modifier = Modifier.size(24.dp),
                    )
                } else {
                    Text(
                        text = buttonText,
                        style = typography.titleMedium,
                        modifier = Modifier.alpha(if (isSubscribed) .7f else 1f),
                    )
                }
            }
        }
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
            text = stringResource(R.string.auto_renews_cancel),
            fontSize = 13.sp,
            letterSpacing = 0.6.sp,
            color = Color.White,
        )
        Spacer(Modifier.height(2.dp))
        PolicyRow(context = LocalContext.current, fontSize = 11.sp)
    }
}

/** 权益对比表格的一行数据：左侧为权益名称，中间为 Free 列文案，右侧为 Premium 列文案。 */
data class BenefitRow(val label: String, val free: String, val premium: String)

/**
 * 订阅页「Benefit Details」对比表格：Free | Premium 两列，多行权益对比。
 * 使用 MaterialTheme 颜色与字体。
 */
@Composable
fun BenefitDetailsTable(
    rows: List<BenefitRow>,
    modifier: Modifier = Modifier,
    headerTitle: String = stringResource(R.string.subscription_benefit_details_title),
    freeColumnTitle: String = stringResource(R.string.subscription_benefit_free),
    premiumColumnTitle: String = stringResource(R.string.subscription_benefit_premium),
) {
    val colorScheme = MaterialTheme.colorScheme
    val typography = MaterialTheme.typography
    val textColor = Color(0xFFEAD1FF)

    Surface(
        modifier = modifier,
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surfaceContainer
    ) {
        LazyColumn(
            modifier = Modifier
        ) {
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(40.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "$headerTitle >",
                        style = typography.titleSmall,
                        color = textColor,
                        modifier = Modifier.weight(2f)
                            .padding(start = dimensionResource(R.dimen.padding_large))
                    )
                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .weight(1f)
                            .background(
                                color = MaterialTheme.colorScheme.surface
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = freeColumnTitle,
                            style = typography.labelLarge,
                            color = textColor
                        )
                    }

                    Box(
                        modifier = Modifier.weight(1f),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = premiumColumnTitle,
                            style = typography.labelLarge,
                            color = textColor,
                        )
                    }
                }
            }

            itemsIndexed(rows) { index, row ->
                Row(
                    modifier = Modifier
                        .height(IntrinsicSize.Max)
                        .fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    val containerColor = if (index % 2 == 0) {
                        Color.Transparent
                    } else {
                        MaterialTheme.colorScheme.surfaceContainerLow
                    }

                    Box(
                        contentAlignment = Alignment.CenterStart,
                        modifier = Modifier
                            .weight(2f)
                            .background(containerColor)
                            .padding(
                                start = dimensionResource(R.dimen.padding_large),
                                top = dimensionResource(R.dimen.padding_small),
                                bottom = dimensionResource(R.dimen.padding_small)
                            ),
                    ) {
                        Text(
                            text = row.label,
                            style = typography.bodyLarge,
                            color = textColor,
                        )
                    }

                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .weight(1f)
                            .background(
                                color = MaterialTheme.colorScheme.surface
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = row.free,
                            style = typography.labelLarge,
                            color = textColor,
                            textAlign = TextAlign.Center
                        )
                    }

                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .fillMaxHeight()
                            .weight(1f)
                            .background(containerColor),
                    ) {
                        Text(
                            text = row.premium,
                            style = typography.labelLarge,
                            color = textColor,
                            textAlign = TextAlign.Center
                        )
                    }
                }
            }
        }
    }

}

/** 订阅页使用的 12 条权益对比行（Free | Premium），与文档 订阅页修改0304 一致。 */
@Composable
fun subscriptionBenefitRows(): List<BenefitRow> =
    listOf(
        BenefitRow(
            stringResource(R.string.benefit_daily_chat),
            stringResource(R.string.benefit_value_limited),
            stringResource(R.string.benefit_value_unlimited),
        ),
        BenefitRow(
            stringResource(R.string.benefit_chat_memory),
            stringResource(R.string.benefit_value_short_term),
            stringResource(R.string.benefit_value_long_term),
        ),
        BenefitRow(stringResource(R.string.benefit_customize_chat_style), stringResource(R.string.benefit_value_dash), stringResource(R.string.benefit_value_check)),
        BenefitRow(stringResource(R.string.benefit_smarter_ai_model), stringResource(R.string.benefit_value_dash), stringResource(R.string.benefit_value_check)),
        BenefitRow(
            stringResource(R.string.benefit_voice),
            stringResource(R.string.benefit_value_limited),
            stringResource(R.string.benefit_value_unlimited),
        ),
        BenefitRow(stringResource(R.string.benefit_hd_voice), stringResource(R.string.benefit_value_dash), stringResource(R.string.benefit_value_check)),
        BenefitRow(
            stringResource(R.string.benefit_voice_call_time),
            stringResource(R.string.benefit_value_5_min_per_day),
            stringResource(R.string.benefit_value_30_min_per_day),
        ),
        BenefitRow(stringResource(R.string.benefit_more_image_generations), stringResource(R.string.benefit_value_dash), stringResource(R.string.benefit_value_check)),
        BenefitRow(
            stringResource(R.string.benefit_photo_quality),
            stringResource(R.string.benefit_value_standard),
            stringResource(R.string.benefit_value_hd),
        ),
        BenefitRow(stringResource(R.string.benefit_vip_exclusive_characters), stringResource(R.string.benefit_value_dash), stringResource(R.string.benefit_value_check)),
        BenefitRow(stringResource(R.string.benefit_early_access_new_features), stringResource(R.string.benefit_value_dash), stringResource(R.string.benefit_value_check)),
        BenefitRow(stringResource(R.string.benefit_advanced_functions), stringResource(R.string.benefit_value_dash), stringResource(R.string.benefit_value_check)),
    )

/** 空状态组件，使用 MaterialTheme 颜色与字体。 */
@Composable
fun EmptyPlanState(modifier: Modifier = Modifier) {
    val colorScheme = MaterialTheme.colorScheme
    val typography = MaterialTheme.typography
    Text(
        text = stringResource(R.string.no_subscription_plans),
        style = typography.bodyLarge,
        color = colorScheme.onBackground.copy(alpha = 0.6f),
        textAlign = TextAlign.Center,
        modifier = modifier.fillMaxWidth(),
    )
}

@Preview
@Composable
private fun BenefitDetailsTablePreview() {
    IntelliMateTheme {
        BenefitDetailsTable(
            rows = subscriptionBenefitRows(),
            modifier = Modifier
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun PremiumBenefitItemPreview() {
    PremiumBenefitItem("无限对话次数")
}

@Preview(showBackground = true)
@Composable
private fun PurchaseButtonPreview() {
    PurchaseButton(isSubscribed = false, hasSelectedPlan = true, onPurchase = {}, isLoading = false)
}
