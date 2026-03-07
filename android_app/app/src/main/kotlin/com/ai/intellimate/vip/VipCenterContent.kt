package com.ai.intellimate.vip

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.firebase.logEvent
import ai.sxwl.android.utils.LogUtils
import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.MainActivity
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.BenefitDetailsTable
import com.ai.intellimate.ui.components.EmptyPlanState
import com.ai.intellimate.ui.components.PremiumPlanList
import com.ai.intellimate.ui.components.PurchaseButton
import com.ai.intellimate.ui.components.subscriptionBenefitRows
import com.ai.intellimate.utils.TextStyleUtils
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling

/** 会员中心页面主内容 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VipCenterContent(
    navController: NavController,
    //    onClose: () -> Unit,
    //    onPurchase: () -> Unit,
    viewModel: VipCenterViewModel = viewModel(),
    pageFrom: String? = null,
) {
    val plans by viewModel.plansFlow.collectAsState()
    val selectedPlanIndex by viewModel.selectedPlanIndex.collectAsState()
    val vipStatus by viewModel.vipStatusFlow.collectAsState()
    val isPurchasing by viewModel.isPurchasing.collectAsState()

    val context = LocalContext.current
    // 通过扩展函数获取 Activity
    val activity = context.findActivity()
    fun onPurchase() {
        if (activity is MainActivity) {
            viewModel.purchaseSelectedPlan(activity)
        }
    }

    fun onClose() {
        navController.popBackStack()
    }

    // 当UI显示价格时，上报Firebase事件（100%采样）
    // 使用plans的key来避免重复上报相同的价格信息
    val plansKey =
        remember(plans) {
            plans.joinToString("|") {
                "${it.googleProductId}:${it.price}:${it.currencyCode}:${it.priceAmountMicros}"
            }
        }

    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView("subscriptionPage")

        FirebaseManager.Events.SUBSCRIPTION_PAGE_VIEW.logEvent(
            "page_source" to (pageFrom ?: "unknown")
        )
    }

    LaunchedEffect(plansKey) {
        if (plans.isNotEmpty()) {
            try {
                // 为每个计划上报价格查看事件
                plans.forEach { plan ->
                    FirebaseManager.logEvent(
                        FirebaseManager.Events.SUBSCRIPTION_PRICE_VIEW,
                        FirebaseManager.safeEventParams(
                            "product_id" to plan.googleProductId,
                            "product_name" to (plan.name ?: ""),
                            "plan_type" to (plan.planType ?: ""),
                            "price" to (plan.price ?: "-"),
                            "currency_code" to (plan.currencyCode ?: ""),
                            "price_micros" to plan.priceAmountMicros,
                            "timestamp" to System.currentTimeMillis(),
                        ),
                    )
                }
                LogUtils.d(
                    "Billing VipCenterContent - ✅ Firebase事件已上报: SUBSCRIPTION_PRICE_VIEW, 计划数量: ${plans.size}"
                )
            } catch (e: Exception) {
                LogUtils.e("Billing VipCenterContent - ⚠️ Firebase事件上报失败: ${e.message}")
            }
        }
    }

    val colorScheme = MaterialTheme.colorScheme
    val typography = MaterialTheme.typography
    Box(modifier = Modifier.fillMaxSize().background(colorScheme.background)) {
        val selectedPlan = plans.getOrNull(selectedPlanIndex)
        val scrollState = rememberScrollState()
        Column(modifier = Modifier.fillMaxSize()) {
            VipCenterTopBar(onClose = { onClose() })

            // 顶部标题与副标题（参考 订阅页修改0304：非订阅/订阅状态不同文案）
            SubscriptionPageHeader(isSubscribed = vipStatus.isSubscribed)

            Spacer(Modifier.height(12.dp))
            if (plans.isNotEmpty()) {
                IgnoreSystemFontScaling {
                    PremiumPlanList(
                        plans = plans,
                        selectedIndex = selectedPlanIndex,
                        isSubscribed = vipStatus.isSubscribed,
                        onPlanSelected = { index ->
                            viewModel.selectPlan(index)
                            FirebaseManager.Events.SUBSCRIPTION_CTA_CLICK.logEvent(
                                "click_type" to
                                    when (index) {
                                        0 -> "monthly"
                                        1 -> "quarterly"
                                        2 -> "annually"
                                        else -> "unknown"
                                    }
                            )
                        },
                    )
                }
                // 当前选中计划价格与续费说明（参考 Talkie+）
                if (selectedPlan != null) {
                    Text(
                        text =
                            stringResource(
                                R.string.subscription_billing_cycle_notice,
                                selectedPlan.price,
                            ),
                        modifier =
                            Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(top = 8.dp),
                        style = typography.labelSmall,
                        color = colorScheme.onBackground.copy(alpha = 0.85f),
                    )
                }
                Spacer(Modifier.height(16.dp))
                BenefitDetailsTable(rows = subscriptionBenefitRows())

                Spacer(Modifier.weight(1f).heightIn(min = 16.dp))
                PurchaseButton(
                    isSubscribed = vipStatus.isSubscribed,
                    hasSelectedPlan = viewModel.hasSelectedPlan(),
                    onPurchase = { onPurchase() },
                    isLoading = isPurchasing,
                    selectedPlanPrice = selectedPlan?.price,
                )
                Spacer(Modifier.height(12.dp))
                // 会员与续订条款链接（参考 Talkie+ 底部）
                Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    TextStyleUtils.BuildLink(
                        context = context,
                        text = stringResource(R.string.membership_renewal_terms),
                        url = context.getString(R.string.url_user_agreement),
                        fontSize = 12.sp,
                    )
                }
            } else {
                EmptyPlanState()
            }
            Spacer(Modifier.height(40.dp))
        }
    }
}

/** 会员中心顶部栏 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VipCenterTopBar(onClose: () -> Unit) {
    val colorScheme = MaterialTheme.colorScheme
    CenterAlignedTopAppBar(
        title = { Text(text = "", fontWeight = FontWeight(600), color = colorScheme.onBackground) },
        modifier = Modifier.fillMaxWidth(),
        navigationIcon = {
            IconButton(onClick = onClose) {
                Image(
                    painter = painterResource(R.drawable.back),
                    contentDescription = stringResource(R.string.content_desc_back),
                )
            }
        },
        colors = TopAppBarDefaults.topAppBarColors().copy(containerColor = colorScheme.background),
    )
}

/** 订阅页顶部标题与副标题（参考 订阅页修改0304：非订阅 / 订阅状态不同文案）。 */
@Composable
private fun SubscriptionPageHeader(isSubscribed: Boolean) {
    val colorScheme = MaterialTheme.colorScheme
    val typography = MaterialTheme.typography
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        Text(
            text =
                if (isSubscribed) {
                    stringResource(R.string.subscription_page_title_subscribed)
                } else {
                    stringResource(R.string.subscription_page_title_upgrade)
                },
            style = typography.titleLarge,
            color = colorScheme.onBackground,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            text =
                if (isSubscribed) {
                    stringResource(R.string.subscription_page_subtitle_subscribed)
                } else {
                    stringResource(R.string.subscription_page_subtitle_upgrade)
                },
            style = typography.bodyLarge,
            color = colorScheme.onBackground.copy(alpha = 0.9f),
        )
    }
}

// Context 扩展函数：安全地查找 Activity
fun Context.findActivity(): Activity? =
    when (this) {
        is Activity -> this // 已经是 Activity，直接返回
        is ContextWrapper -> baseContext.findActivity() // 继续解包 baseContext
        else -> null // 无法找到
    }
