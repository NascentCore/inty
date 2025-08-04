package com.ai.inty

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.VideoView
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.net.toUri
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import com.ai.inty.billing.VipPlan
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.VipCenterViewModel
import com.therouter.router.Route

/**
 * 会员中心页面，展示会员权益与订阅选项。
 */
@Route(path = Constant.ROUTE_VIP_CENTER)
class VipCenterActivity : BaseActivity() {
    private val viewModel: VipCenterViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            IntyTheme {
                VipCenterScreen(
                    onClose = { finish() },
                    viewModel = viewModel,
                    onPurchase = { viewModel.purchaseSelectedPlan(this) }
                )
            }
        }
    }
}

/**
 * IntelliMate Premium 会员中心静态UI。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VipCenterScreen(
    onClose: () -> Unit = { },
    viewModel: VipCenterViewModel,
    onPurchase: () -> Unit = { },
) {
    val plans by viewModel.plansFlow.collectAsState()
    val selectedPlanIndex by viewModel.selectedPlanIndex.collectAsState()
    val vipStatus by viewModel.vipStatusFlow.collectAsState()
    val context = LocalContext.current

    Box(modifier = Modifier.fillMaxSize()) {
        // 全屏视频播放器
        BackgroundVideoPlayer()

        // 半透明遮罩层，确保内容可读性
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(.77f)
                .align(Alignment.BottomCenter)
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color(0x001C1523),
                            Color(0xA81C1523),
                            Color(0xE31C1523),
                            Color(0xFF1C1523),
                        )
                    )
                )
        )

        Column(modifier = Modifier.fillMaxSize()) {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.premium_title),
                        fontWeight = FontWeight(600),
                        color = Color.White
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                navigationIcon = {
                    IconButton(onClick = onClose) {
                        Image(
                            painter = painterResource(R.drawable.back),
                            contentDescription = "back"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors()
                    .copy(containerColor = Color.Transparent)
            )
            Spacer(Modifier.height(110.dp))

            Column(modifier = Modifier.padding(start = 16.dp)) {

                Image(
                    painter = painterResource(R.drawable.img_heartmate_premium),
                    contentDescription = null,
                    modifier = Modifier.size(278.dp, 32.dp)
                )
                Text(
                    text = stringResource(R.string.premium_subtitle),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.White,
                )

                PremiumBenefitItem(stringResource(R.string.premium_benefit_unlimited))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_model))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_inspiration))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_customize))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_memory))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_newfeature))

            }

            Spacer(Modifier.height(32.dp))

            // 动态显示订阅计划列表
            if (plans.isNotEmpty()) {
                PremiumPlanList(
                    plans = plans,
                    selectedIndex = selectedPlanIndex,
                    isSubscribed = vipStatus.isSubscribed,
                    onPlanSelected = { index -> viewModel.selectPlan(index) }
                )

                Spacer(Modifier.height(32.dp))

                //按钮
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 15.dp)
                        .height(56.dp)
                        .clip(RoundedCornerShape(28.dp))
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(
                                    Color(0xFF9756FF),
                                    Color(0xFFEF56FF)
                                )
                            )
                        )
                        .alpha(if (vipStatus.isSubscribed) .4f else 1f)
                        .clickable(
                            enabled = !vipStatus.isSubscribed && viewModel.hasSelectedPlan(),
                            onClick = onPurchase
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = if (vipStatus.isSubscribed) {
                            stringResource(R.string.premium_subscribed)
                        } else {
                            stringResource(R.string.premium_continue)
                        },
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.alpha(if (vipStatus.isSubscribed) .7f else 1f)
                    )
                }

            } else {
                // 无订阅计划数据时显示空状态
                Text(
                    text = "暂无订阅计划信息",
                    color = Color.White.copy(alpha = 0.6f),
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            Spacer(Modifier.height(16.dp))

            Text(
                text = stringResource(R.string.premium_autorenew),
                fontSize = 12.sp,
                color = Color.White,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                val policyStr = buildAnnotatedString {
                    withStyle(SpanStyle(textDecoration = TextDecoration.Underline)) {
                        append(stringResource(R.string.privacy_policy))
                    }
                }
                Text(
                    text = policyStr,
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.6f),
                    modifier = Modifier.noRippleClickable(onClick = {
                        val intent = Intent(
                            Intent.ACTION_VIEW,
                            context.getString(R.string.settings_str_privacy_policy).toUri()
                        )
                        context.startActivity(intent)
                    })
                )

                Text(text = " & ", color = Color.White.copy(alpha = 0.6f), fontSize = 12.sp)
                val termsOfUse = buildAnnotatedString {
                    withStyle(SpanStyle(textDecoration = TextDecoration.Underline)) {
                        append(stringResource(R.string.terms_of_use))
                    }
                }
                Text(
                    text = termsOfUse,
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.6f),
                    modifier = Modifier.noRippleClickable(onClick = {
                        val intent = Intent(
                            Intent.ACTION_VIEW,
                            context.getString(R.string.settings_str_user_agreement).toUri()
                        )
                        context.startActivity(intent)
                    })
                )
            }
            Spacer(Modifier.height(20.dp))
        }
    }
}

/**
 * 自定义全屏视频播放器。
 * 继承VideoView并重写onMeasure方法确保全屏显示。
 */
private class FullScreenVideoView(context: android.content.Context) : VideoView(context) {

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = getDefaultSize(0, widthMeasureSpec)
        val height = getDefaultSize(0, heightMeasureSpec)
        setMeasuredDimension(width, height)
    }
}

/**
 * 背景视频播放器组件。
 * 使用AndroidView包装自定义VideoView，实现循环播放和性能优化。
 */
@Composable
private fun BackgroundVideoPlayer() {
    AndroidView(
        factory = { ctx ->
            FrameLayout(ctx).apply {
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )

                val videoView = FullScreenVideoView(ctx).apply {
                    layoutParams = FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        Gravity.CENTER
                    )

                    // 设置视频路径
                    val videoPath = "android.resource://${ctx.packageName}/raw/subscribe_bg"
                    setVideoURI(Uri.parse(videoPath))

                    // 设置循环播放
                    setOnPreparedListener { mediaPlayer ->
                        mediaPlayer.isLooping = true
                        // 静音播放，避免干扰用户体验
                        mediaPlayer.setVolume(0f, 0f)
                    }

                    // 开始播放
                    start()
                }

                addView(videoView)
            }
        },
        modifier = Modifier.fillMaxSize(),
        update = { frameLayout ->
            // 组件更新时的处理逻辑
        }
    )

    // 组件销毁时停止播放
    DisposableEffect(Unit) {
        onDispose {
            // 这里不需要手动停止，VideoView会在Activity销毁时自动清理
        }
    }
}


/**
 * 会员权益项。
 */
@Composable
private fun PremiumBenefitItem(text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(vertical = 2.dp)
    ) {
        Image(
            painter = painterResource(id = R.drawable.ic_checked_premium),
            contentDescription = null,
            modifier = Modifier.size(16.dp)
        )
        Spacer(Modifier.width(8.dp))
        Text(text = text, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Light)
    }
    Spacer(Modifier.height(4.dp))
}

/**
 * 订阅计划列表动态UI。
 * @param plans 订阅计划列表
 * @param selectedIndex 选中的计划索引
 * @param isSubscribed 是否已订阅
 * @param onPlanSelected 选择计划回调
 */
@Composable
private fun PremiumPlanList(
    plans: List<VipPlan>,
    selectedIndex: Int,
    isSubscribed: Boolean,
    onPlanSelected: (Int) -> Unit,
) {
    val subModifier = if (isSubscribed) Modifier.alpha(.4f) else Modifier
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(132.dp)
            .padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {

        plans.forEachIndexed { idx, plan ->

            val isSelected = idx == selectedIndex

            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .weight(1f)
                    .background(
                        color = if (isSelected) Color(0x99350D5D) else Color(0x991C1523),
                        shape = RoundedCornerShape(8.dp)
                    )
                    .border(
                        width = 1.dp,
                        color = if (isSelected) Color.White else Color.Transparent,
                        shape = RoundedCornerShape(8.dp)
                    )
                    .then(subModifier)
                    .clickable(enabled = !isSubscribed) { onPlanSelected(idx) }
                    .padding(vertical = 8.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = plan.name, // 显示计划名称
                    color = when {
                        isSubscribed -> Color.White.copy(alpha = 0.5f) // 已订阅用户显示灰色
                        else -> Color.White // 正常状态
                    },
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .then(subModifier)
                )
                val priceStr = buildAnnotatedString {
                    append(plan.price.substringBefore('$'))
                    append("$")
                    withStyle(style = SpanStyle(fontSize = 24.sp, fontWeight = FontWeight.Bold)) {
                        append(plan.price.substringAfterLast('$'))
                    }
                }
                Text(
                    text = priceStr, // 显示计划价格
                    color = when {
                        isSubscribed -> Color.White.copy(alpha = 0.5f) // 已订阅用户显示灰色
                        else -> Color.White // 正常状态
                    },
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Normal,
                    modifier = subModifier
                )
                //折扣
                if (plan.discountRate < 1) {
                    Box(
                        Modifier
                            .size(64.dp, 22.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(
                                brush = Brush.horizontalGradient(
                                    colors = listOf(
                                        Color(0xFFC1F9FD),
                                        Color(0xFFD4AEFD),
                                        Color(0xFF7B96FB),
                                    )
                                )
                            )
                            .then(subModifier)
                            .align(Alignment.BottomCenter),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Save ${((1 - plan.discountRate) * 100).toInt()}/%", // 显示计划价格
                            color = Color.Black,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = subModifier
                        )
                    }
                }

            }
        }
    }
}

/**
 * 会员中心页面预览。
 */
@SuppressLint("ViewModelConstructorInComposable")
@Preview(showBackground = true, backgroundColor = 0xFF23232B)
@Composable
private fun VipCenterScreenPreview() {
    // 预览时使用模拟数据
    VipCenterScreen(
        onClose = {},
        viewModel = VipCenterViewModel(),
        onPurchase = {}
    )
}