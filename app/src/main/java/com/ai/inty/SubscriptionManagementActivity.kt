package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModelProvider
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import com.ai.inty.billing.BillingRepository
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.SubscriptionManagementViewModel
import com.ai.inty.viewmodels.SubscriptionUiEvent
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import com.therouter.router.Route

/**
 * 订阅管理页面
 */
@Route(path = Constant.ROUTE_SUBSCRIPTION_MANAGEMENT)
class SubscriptionManagementActivity : BaseActivity() {

    private val viewModel: SubscriptionManagementViewModel by lazy {
        ViewModelProvider(this)[SubscriptionManagementViewModel::class.java]
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            IntyTheme {
                SubscriptionManagementScreen(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(BackGround),
                    onBack = {
                        finish()
                    },
                    viewModel = viewModel
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SubscriptionManagementScreen(
    modifier: Modifier,
    onBack: () -> Unit,
    viewModel: SubscriptionManagementViewModel,
) {
    val context = LocalContext.current
    
    // 获取订阅状态
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    // 观察来自 ViewModel 的 UI 事件
    LaunchedEffect(Unit) {
        viewModel.uiEvent.collect { event ->
            when (event) {
                SubscriptionUiEvent.NavigateToPlayStoreSubscriptions -> {
                    // 在View层执行实际的Intent启动
                    openPlayStoreSubscriptions(context)
                }
                is SubscriptionUiEvent.ShowToast -> {
                    Toast.makeText(context, event.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.settings_subscription_management),
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 20.sp,
                    )
                },
                navigationIcon = {
                    Image(
                        modifier = Modifier
                            .padding(horizontal = 12.dp)
                            .noRippleClickable {
                                onBack()
                            },
                        painter = painterResource(R.drawable.back),
                        contentDescription = null,
                    )
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier.padding(innerPadding)
        ) {
            Column(
                modifier = Modifier
                    .padding(horizontal = 16.dp)
                    .fillMaxWidth()
                    .border(
                        brush = Brush.linearGradient(
                            colors = listOf(
                                Color.Transparent,
                                Color.White.copy(0.2f),
                                Color.Transparent
                            )
                        ),
                        width = 1.dp,
                        shape = RoundedCornerShape(8.dp)
                    )
                    .background(
                        color = Color(0x3378599A),
                        shape = RoundedCornerShape(8.dp)
                    )
            ) {
                Spacer(Modifier.height(8.dp))
                
                if (vipStatus.isSubscribed) {
                    // 已订阅状态：显示取消订阅
                    SubscriptionManagementItem(
                        icon = R.drawable.icon_list_row_3,
                        title = stringResource(R.string.cancel_subscription),
                        onClick = {
                            viewModel.navigateToGooglePlaySubscription()
                        }
                    )
                } else {
                    // 未订阅状态：显示恢复订阅
                    SubscriptionManagementItem(
                        icon = R.drawable.icon_list_row_1,
                        title = stringResource(R.string.restore_subscription),
                        onClick = {
                            viewModel.navigateToGooglePlaySubscription()
                        }
                    )
                }
                
                // 分隔线
                Spacer(Modifier.height(4.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(1.dp)
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(
                                    Color.Transparent,
                                    Color.White.copy(0.2f),
                                    Color.Transparent
                                )
                            )
                        )
                )
                Spacer(Modifier.height(4.dp))
                
                // 兑换码（两种状态都显示）
                SubscriptionManagementItem(
                    icon = R.drawable.icon_list_row_2,
                    title = stringResource(R.string.redemption_code),
                    onClick = {
                        viewModel.navigateToGooglePlaySubscription()
                    }
                )
                
                Spacer(Modifier.height(8.dp))
            }
        }
    }
}

@Composable
fun SubscriptionManagementItem(
    icon: Int,
    title: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .padding(horizontal = 12.dp)
            .noRippleClickable { onClick() },
        verticalAlignment = Alignment.CenterVertically
    ) {
        // 图标
        Box(
            modifier = Modifier
                .size(32.dp)
                .background(
                    color = when (icon) {
                        R.drawable.icon_list_row_1 -> Color(0xFF2196F3) // 蓝色
                        R.drawable.icon_list_row_2 -> Color(0xFFE91E63) // 粉色
                        R.drawable.icon_list_row_3 -> Color(0xFFFF9800) // 橙色
                        else -> Color(0xFF9C27B0) // 默认紫色
                    },
                    shape = RoundedCornerShape(6.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(icon),
                contentDescription = null,
                modifier = Modifier.size(20.dp)
            )
        }
        
        Spacer(Modifier.width(12.dp))
        
        // 标题
        Text(
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White
        )
        
        Spacer(Modifier.weight(1f))
        
        // 右箭头
        Image(
            painter = painterResource(R.drawable.icon_next),
            contentDescription = null,
        )
    }
}

/**
 * 实际执行跳转逻辑的辅助函数，放置在Composable外部。
 * 它需要 Context 参数来启动 Intent。
 */
private fun openPlayStoreSubscriptions(context: android.content.Context) {
    try {
        val uri = Uri.parse("https://play.google.com/store/account/subscriptions")
        val intent = Intent(Intent.ACTION_VIEW, uri)

        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
            EasyLog.log("✅ 成功跳转到 Google Play 订阅管理页面")
        } else {
            EasyLog.log("❌ 没有找到可以处理 Google Play 订阅管理页面的应用")
            Toast.makeText(context, "无法打开 Google Play 商店。", Toast.LENGTH_LONG).show()
        }
    } catch (e: Exception) {
        EasyLog.log("❌ 跳转到 Google Play 订阅管理页面失败: ${e.message}")
        Toast.makeText(context, "跳转失败，请稍后再试。", Toast.LENGTH_LONG).show()
    }
}