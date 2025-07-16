package com.ai.inty

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
 * HeartMate Premium 会员中心静态UI。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VipCenterScreen(
    onClose: () -> Unit = { },
    viewModel: VipCenterViewModel,
    onPurchase: () -> Unit = { }
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
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.7f))
        )

        Column(modifier = Modifier.fillMaxSize()) {
            CenterAlignedTopAppBar(
                title = {
                    Text(text = stringResource(R.string.premium_title))
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
            Spacer(Modifier.height(80.dp))

            Column(modifier = Modifier.padding(start = 20.dp)) {

                Text(
                    text = stringResource(R.string.premium_title),
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    modifier = Modifier
                        .padding(bottom = 6.dp)
                        .fillMaxWidth(),
                    textAlign = TextAlign.Start
                )

                Text(
                    text = stringResource(R.string.premium_subtitle),
                    fontSize = 14.sp,
                    color = Color.White.copy(alpha = 0.8f),
                    textAlign = TextAlign.Start,
                    modifier = Modifier
                        .padding(bottom = 16.dp)
                        .fillMaxWidth()
                )

                PremiumBenefitItem(stringResource(R.string.premium_benefit_unlimited))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_model))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_inspiration))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_customize))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_memory))
                PremiumBenefitItem(stringResource(R.string.premium_benefit_newfeature))

            }

            Spacer(Modifier.height(20.dp))

            // 动态显示订阅计划列表
            if (plans.isNotEmpty()) {
                PremiumPlanList(
                    plans = plans,
                    selectedIndex = selectedPlanIndex,
                    isSubscribed = vipStatus.isSubscribed,
                    onPlanSelected = { index -> viewModel.selectPlan(index) }
                )

                Spacer(Modifier.height(30.dp))

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp)
                        .height(48.dp)
                        .clip(RoundedCornerShape(24.dp))
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(
                                    Color(0xFF7C4DFF),
                                    Color(0x357C4DFF)
                                )
                            )
                        )
                        .noRippleClickable(onClick = onPurchase),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = if (vipStatus.isSubscribed) {
                            stringResource(R.string.premium_subscribed)
                        } else {
                            stringResource(R.string.premium_continue)
                        },
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
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

            Spacer(Modifier.weight(1f))

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
                            Uri.parse("https://app.termly.io/policy-viewer/policy.html?policyUUID=c82c3bfa-10a0-4075-a7f1-a98d5146d71c")
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
                            Uri.parse("https://app.termly.io/policy-viewer/policy.html?policyUUID=97416d63-aebb-4ea5-b990-eccc5aa6cff1")
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
            painter = painterResource(id = R.drawable.checked),
            contentDescription = null,
            modifier = Modifier.size(18.dp)
        )
        Spacer(Modifier.width(8.dp))
        Text(text = text, color = Color.White, fontSize = 14.sp)
    }
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
    onPlanSelected: (Int) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(150.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {

        plans.forEachIndexed { idx, plan ->

            val isSelected = idx == selectedIndex

            Column(
                modifier = Modifier
                    .fillMaxHeight()
                    .weight(1f)
                    .background(
                        color = if (isSelected) Color(0x6623232B) else Color(0xFF23232B),
                        shape = RoundedCornerShape(12.dp)
                    )
                    .border(
                        width = 1.dp,
                        color = if (isSelected) Color.White else Color.Transparent,
                        shape = RoundedCornerShape(12.dp)
                    )
                    .padding(horizontal = 12.dp)
                    .clickable(enabled = !isSubscribed) { onPlanSelected(idx) },
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = plan.name, // 显示计划名称
                    color = when {
                        isSubscribed -> Color.White.copy(alpha = 0.5f) // 已订阅用户显示灰色
                        else -> Color.White // 正常状态
                    },
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    modifier = Modifier.weight(1f)
                )

                Text(
                    text = plan.price, // 显示计划价格
                    color = when {
                        isSubscribed -> Color.White.copy(alpha = 0.5f) // 已订阅用户显示灰色
                        else -> Color.White // 正常状态
                    },
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
                //折扣
                if (plan.discountRate < 1) {
                    Box(
                        Modifier
                            .size(80.dp, 36.dp)
                            .clip(RoundedCornerShape(20.dp))
                            .background(
                                brush = Brush.horizontalGradient(
                                    colors = listOf(
                                        Color.Yellow,
                                        Color.Cyan
                                    )
                                )
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Save ${plan.discountRate * 100}/%", // 显示计划价格
                            color = Color.Black,
                            fontSize = 14.sp
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