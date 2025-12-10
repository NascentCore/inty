package com.ai.intellimate.vip

import ai.sxwl.android.firebase.FirebaseManager
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.MainActivity
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.AutoRenewalNotice
import com.ai.intellimate.ui.components.EmptyPlanState
import com.ai.intellimate.ui.components.PremiumBenefitItem
import com.ai.intellimate.ui.components.PremiumPlanList
import com.ai.intellimate.ui.components.PurchaseButton
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling
import dev.chrisbanes.haze.HazeState
import dev.chrisbanes.haze.hazeEffect
import dev.chrisbanes.haze.hazeSource
import dev.chrisbanes.haze.rememberHazeState

/** 订阅描述文本组件 */
@Composable
private fun SubscriptionDescriptionText(text: String) {
    Text(
        text = text,
        color = Color.Gray,
        fontSize = 14.sp,
        fontWeight = FontWeight.Normal,
        textAlign = TextAlign.Center,
        // 保证文字居中
        modifier = Modifier.fillMaxWidth(),
    )
}

/** 会员中心页面主内容 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VipCenterContent(
    navController: NavController,
    //    onClose: () -> Unit,
    //    onPurchase: () -> Unit,
    viewModel: VipCenterViewModel = viewModel(),
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

    Box(
        modifier =
            Modifier.fillMaxSize().background(ai.sxwl.android.design.theme.HeartColor.primaryColor)
    ) {
        // 双层图片背景
        val hazeState = rememberHazeState()
        Image(
            painter = painterResource(R.drawable.vip_bg),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )
        Box(modifier = Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.7f)))
        Image(
            painter = painterResource(R.drawable.vip_female),
            contentDescription = null,
            modifier = Modifier.fillMaxSize().padding(top = 100.dp).hazeSource(state = hazeState),
            alignment = Alignment.BottomCenter,
            contentScale = ContentScale.FillHeight,
        )

        val scrollState = rememberScrollState()
        Column(modifier = Modifier.fillMaxSize().verticalScroll(scrollState)) {
            VipCenterTopBar(onClose = { onClose() })

            Spacer(Modifier.weight(1f))
            VipBenefitsDesc(hazeState)

            Spacer(Modifier.height(12.dp))
            // 动态显示订阅计划列表
            if (plans.isNotEmpty()) {
                IgnoreSystemFontScaling {
                    PremiumPlanList(
                        plans = plans,
                        selectedIndex = selectedPlanIndex,
                        isSubscribed = vipStatus.isSubscribed,
                        onPlanSelected = { index -> viewModel.selectPlan(index) },
                    )
                }

                PurchaseButton(
                    isSubscribed = vipStatus.isSubscribed,
                    hasSelectedPlan = viewModel.hasSelectedPlan(),
                    onPurchase = { onPurchase() },
                    isLoading = isPurchasing,
                )
            } else {
                EmptyPlanState()
            }

            AutoRenewalNotice()
            Spacer(Modifier.height(40.dp))
        }
    }
}

/** 会员中心顶部栏 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VipCenterTopBar(onClose: () -> Unit) {
    CenterAlignedTopAppBar(
        title = { Text(text = "", fontWeight = FontWeight(600), color = Color.White) },
        modifier = Modifier.fillMaxWidth(),
        navigationIcon = {
            IconButton(onClick = onClose) {
                Image(
                    painter = painterResource(R.drawable.back),
                    contentDescription = stringResource(R.string.content_desc_back),
                )
            }
        },
        colors = TopAppBarDefaults.topAppBarColors().copy(containerColor = Color.Transparent),
    )
}

/** 会员中心头部 */
@Composable
private fun VipCenterHeader() {
    Column(modifier = Modifier.padding(start = 16.dp)) {
        Image(
            painter = painterResource(R.drawable.img_intellimate_premium),
            contentDescription = null,
            modifier = Modifier.size(278.dp, 32.dp),
        )
        Text(
            text = stringResource(R.string.premium_subtitle),
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium,
            color = Color.White,
        )
        Spacer(Modifier.height(10.dp))
    }
}

/** 会员权益列表 */
@Composable
private fun VipCenterBenefits() {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        PremiumBenefitItem(stringResource(R.string.premium_benefit_unlimited_chat))

        PremiumBenefitItem(stringResource(R.string.premium_benefit_higher_other_limits))

        PremiumBenefitItem(stringResource(R.string.premium_benefit_model))
        PremiumBenefitItem(stringResource(R.string.premium_benefit_flagship_models))
        PremiumBenefitItem(stringResource(R.string.premium_benefit_chat_style))

        PremiumBenefitItem(stringResource(R.string.premium_benefit_newfeature))
    }
}

@Preview(showBackground = true)
@Composable
private fun VipCenterContentPreview() {
    //    VipCenterContent(onClose = {}, onPurchase = {})
}

@Composable
private fun VipBenefitsDesc(hazeState: HazeState) {
    Box(
        modifier =
            Modifier.fillMaxWidth()
                .padding(start = 16.dp, end = 16.dp)
                .background(Color(0x806E5289).copy(alpha = 0.3f), shape = RoundedCornerShape(8.dp))
                .clip(RoundedCornerShape(8.dp))
                .hazeEffect(state = hazeState) { blurRadius = 4.dp }
    ) {
        Column {
            Spacer(modifier = Modifier.height(16.dp))
            Image(
                painter = painterResource(R.drawable.vip_desc_title),
                contentDescription = null,
                modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp),
                contentScale = ContentScale.FillWidth,
            )

            Spacer(modifier = Modifier.height(30.dp))
            Image(
                painter = painterResource(R.drawable.vip_desc_content),
                contentDescription = null,
                modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp),
                contentScale = ContentScale.FillWidth,
            )

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}

// Context 扩展函数：安全地查找 Activity
fun Context.findActivity(): Activity? =
    when (this) {
        is Activity -> this // 已经是 Activity，直接返回
        is ContextWrapper -> baseContext.findActivity() // 继续解包 baseContext
        else -> null // 无法找到
    }
