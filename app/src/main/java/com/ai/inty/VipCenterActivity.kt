package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.theme.IntyTheme
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.therouter.router.Route
import com.ai.inty.billing.SubscriptionStatus
import androidx.compose.foundation.clickable
import com.ai.inty.viewmodels.VipCenterViewModel
import com.ai.inty.beans.Product

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
                    viewModel = viewModel
                )
            }
        }
    }
}

/**
 * HeartMate Premium 会员中心静态UI。
 */
@Composable
fun VipCenterScreen(
    onClose: (() -> Unit)? = null,
    viewModel: VipCenterViewModel
) {
    val products by viewModel.products.collectAsState()
    val subscriptionStatus by viewModel.subscriptionStatus.collectAsState()
    val selectedSkuIndex by viewModel.selectedSkuIndex.collectAsState()
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(com.ai.inty.ui.theme.BackGround),
        contentAlignment = Alignment.Center
    ) {
        Card(
            modifier = Modifier
                .width(340.dp)
                .wrapContentHeight(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF23232B))
        ) {
            Box(Modifier.fillMaxWidth()) {
                IconButton(
                    onClick = { onClose?.invoke() },
                    modifier = Modifier.align(Alignment.TopEnd)
                ) {
                    Icon(
                        painter = painterResource(id = R.drawable.close),
                        contentDescription = null,
                        tint = Color.White
                    )
                }
            }
            Column(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
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
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = Alignment.Start
                ) {
                    PremiumBenefitItem(stringResource(R.string.premium_benefit_unlimited))
                    PremiumBenefitItem(stringResource(R.string.premium_benefit_model))
                    PremiumBenefitItem(stringResource(R.string.premium_benefit_inspiration))
                    PremiumBenefitItem(stringResource(R.string.premium_benefit_customize))
                    PremiumBenefitItem(stringResource(R.string.premium_benefit_memory))
                    PremiumBenefitItem(stringResource(R.string.premium_benefit_newfeature))
                }
                Spacer(Modifier.height(20.dp))
                
                // 动态显示商品列表
                if (products.isNotEmpty()) {
                    PremiumProductList(
                        products = products,
                        selectedIndex = selectedSkuIndex,
                        isSubscribed = subscriptionStatus is SubscriptionStatus.Subscribed,
                        onProductSelected = { index -> viewModel.selectSku(index) }
                    )
                    Spacer(Modifier.height(12.dp))
                    Button(
                        onClick = { viewModel.purchaseSelectedSku() },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF7C4DFF)
                        ),
                        enabled = subscriptionStatus !is SubscriptionStatus.Subscribed
                    ) {
                        Text(
                            text = if (subscriptionStatus is SubscriptionStatus.Subscribed) {
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
                    // 无商品数据时显示空状态
                    Text(
                        text = "暂无商品信息",
                        color = Color.White.copy(alpha = 0.6f),
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.premium_autorenew),
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.6f),
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center
                ) {
                    TextButton(onClick = { /* TODO: 跳转隐私政策 */ }) {
                        Text(
                            text = stringResource(R.string.privacy_policy),
                            fontSize = 12.sp,
                            color = Color(0xFF7C4DFF)
                        )
                    }
                    Text(text = " & ", color = Color.White.copy(alpha = 0.6f), fontSize = 12.sp)
                    TextButton(onClick = { /* TODO: 跳转服务条款 */ }) {
                        Text(
                            text = stringResource(R.string.terms_of_use),
                            fontSize = 12.sp,
                            color = Color(0xFF7C4DFF)
                        )
                    }
                }
            }
        }
    }
}

/**
 * 会员权益项。
 */
@Composable
fun PremiumBenefitItem(text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(vertical = 2.dp)
    ) {
        Icon(
            painter = painterResource(id = R.drawable.checked),
            contentDescription = null,
            tint = Color(0xFF7C4DFF),
            modifier = Modifier.size(18.dp)
        )
        Spacer(Modifier.width(8.dp))
        Text(text = text, color = Color.White, fontSize = 14.sp)
    }
}

/**
 * 商品列表动态UI。
 * @param products 商品列表
 * @param selectedIndex 选中的商品索引
 * @param isSubscribed 是否已订阅
 * @param onProductSelected 选择商品回调
 */
@Composable
fun PremiumProductList(
    products: List<Product>,
    selectedIndex: Int,
    isSubscribed: Boolean,
    onProductSelected: (Int) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        products.forEachIndexed { idx, product ->
            val isSelected = idx == selectedIndex
            
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
                    .background(
                        color = if (isSelected) Color(0xFFE0D7F7) else Color(0xFF23232B),
                        shape = RoundedCornerShape(12.dp)
                    )
                    .padding(horizontal = 12.dp)
                    .clickable { onProductSelected(idx) },
                contentAlignment = Alignment.CenterStart
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxSize()
                ) {
                    Text(
                        text = product.name, // 显示商品名称
                        color = if (isSelected) Color(0xFF7C4DFF) else Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        text = product.price, // 显示商品价格
                        color = if (isSelected) Color(0xFF7C4DFF) else Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
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
fun VipCenterScreenPreview() {
    // 预览时使用模拟数据
    VipCenterScreen(
        onClose = {},
        viewModel = VipCenterViewModel()
    )
} 