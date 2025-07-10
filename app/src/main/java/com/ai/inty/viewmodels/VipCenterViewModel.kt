package com.ai.inty.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.billing.BillingManager
import com.ai.inty.billing.BillingConfig
import com.ai.inty.billing.SubscriptionStatus
import com.ai.inty.beans.Product
import com.android.billingclient.api.SkuDetails
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import com.inty.utils.log.EasyLog

/**
 * 会员中心ViewModel，管理商品信息和订阅状态。
 */
class VipCenterViewModel : ViewModel() {
    private val _skuDetails = MutableStateFlow<List<SkuDetails>>(emptyList())
    val skuDetails: StateFlow<List<SkuDetails>> = _skuDetails.asStateFlow()
    
    private val _subscriptionStatus = MutableStateFlow<SubscriptionStatus>(SubscriptionStatus.NotSubscribed)
    val subscriptionStatus: StateFlow<SubscriptionStatus> = _subscriptionStatus.asStateFlow()
    
    private val _selectedSkuIndex = MutableStateFlow(0)
    val selectedSkuIndex: StateFlow<Int> = _selectedSkuIndex.asStateFlow()

    // 商品列表，使用数据类封装
    private val _products = MutableStateFlow<List<Product>>(emptyList())
    val products: StateFlow<List<Product>> = _products.asStateFlow()
    
    init {
        // 首先初始化商品列表
        initializeProducts()
        
        // 然后监听BillingManager的商品信息
        viewModelScope.launch {
            BillingManager.skuDetails.collect { skus ->
                _skuDetails.value = skus
                // 当获取到Google Play价格时，更新商品价格
                updateProductPrices(skus)
            }
        }
        // 监听订阅状态
        viewModelScope.launch {
            BillingManager.subscriptionStatus.collect { status ->
                _subscriptionStatus.value = status
            }
        }
    }
    
    /**
     * 初始化商品列表
     */
    private fun initializeProducts() {
        EasyLog.log("=== 初始化商品列表开始 ===")
        val subscriptionIds = BillingConfig.getSubscriptionIds()
        EasyLog.log("从BillingConfig获取商品ID: $subscriptionIds")
        
        if (subscriptionIds.isEmpty()) {
            EasyLog.log("⚠️ 商品ID列表为空，可能原因:")
            EasyLog.log("   1. BillingConfig未正确初始化")
            EasyLog.log("   2. 网络配置未成功加载")
            EasyLog.log("   3. 使用默认配置但默认配置为空")
            _products.value = emptyList()
            EasyLog.log("=== 初始化商品列表结束 ===")
            return
        }
        
        val products = subscriptionIds.map { id ->
            val name = BillingConfig.getSubscriptionDescription(id)
            EasyLog.log("商品配置: ID=$id, 名称=$name")
            Product(
                id = id,
                name = name,
                price = "-", // 初始价格占位符
                originalPrice = "-",
                currencyCode = "",
                priceAmountMicros = 0
            )
        }
        _products.value = products
        EasyLog.log("✅ 成功初始化 ${products.size} 个商品")
        EasyLog.log("=== 初始化商品列表结束 ===")
    }
    
    /**
     * 根据Google Play返回的SkuDetails更新商品价格
     */
    private fun updateProductPrices(skuDetails: List<SkuDetails>) {
        EasyLog.log("=== 商品价格更新开始 ===")
        EasyLog.log("收到Google Play商品数据: ${skuDetails.size} 个商品")
        
        if (skuDetails.isEmpty()) {
            EasyLog.log("❌ Google Play返回的商品列表为空，就跳过价格更新")
            EasyLog.log("=== 商品价格更新结束 ===")
            return
        }
        
        val currentProducts = _products.value.toMutableList()
        if (currentProducts.isEmpty()) {
            EasyLog.log("⚠️ 本地商品列表为空，尝试重新初始化")
            initializeProducts()
            
            // 重新获取初始化后的商品列表
            val reinitializedProducts = _products.value.toMutableList()
            if (reinitializedProducts.isEmpty()) {
                EasyLog.log("❌ 重新初始化后商品列表仍为空，跳过价格更新")
                EasyLog.log("=== 商品价格更新结束 ===")
                return
            }
            EasyLog.log("✅ 重新初始化成功，使用新商品列表继续处理")
            // 使用重新初始化后的商品列表，而不是递归调用
            updateProductPricesWithProducts(skuDetails, reinitializedProducts)
            return
        }
        
        // 使用当前商品列表处理
        updateProductPricesWithProducts(skuDetails, currentProducts)
    }
    
    /**
     * 使用指定的商品列表更新价格（避免递归）
     */
    private fun updateProductPricesWithProducts(skuDetails: List<SkuDetails>, currentProducts: MutableList<Product>) {
        var updatedCount = 0
        var matchedCount = 0
        val localProductIds = currentProducts.map { it.id }
        val skuIds = skuDetails.map { it.sku }
        
        EasyLog.log("本地商品ID列表: $localProductIds")
        EasyLog.log("Google Play返回的商品ID: $skuIds")
        
        // 检查ID匹配情况
        val matchedIds = localProductIds.intersect(skuIds.toSet())
        val unmatchedLocalIds = localProductIds - skuIds.toSet()
        val unmatchedSkuIds = skuIds - localProductIds.toSet()
        
        EasyLog.log("匹配的商品ID: $matchedIds")
        if (unmatchedLocalIds.isNotEmpty()) {
            EasyLog.log("⚠️ 本地有但Google Play没有的商品ID: $unmatchedLocalIds")
        }
        if (unmatchedSkuIds.isNotEmpty()) {
            EasyLog.log("⚠️ Google Play有但本地没有的商品ID: $unmatchedSkuIds")
        }
        
        skuDetails.forEach { sku ->
            val index = currentProducts.indexOfFirst { it.id == sku.sku }
            if (index >= 0) {
                val oldPrice = currentProducts[index].price
                val correctedPrice = correctCurrencySymbol(sku.price, sku.priceCurrencyCode)
                currentProducts[index] = currentProducts[index].copy(price = correctedPrice)
                updatedCount++
                matchedCount++
                EasyLog.log("✅ 更新商品价格: ${sku.sku} - $oldPrice -> $correctedPrice")
                EasyLog.log("   商品标题: ${sku.title}")
                EasyLog.log("   商品描述: ${sku.description}")
                EasyLog.log("   价格分析:")
                EasyLog.log("     原始价格: '${sku.price}'")
                EasyLog.log("     修正后价格: '$correctedPrice'")
                EasyLog.log("     价格金额(微秒): ${sku.priceAmountMicros}")
                EasyLog.log("     货币代码: ${sku.priceCurrencyCode}")
                EasyLog.log("     价格转换: ${sku.priceAmountMicros / 1_000_000.0} ${sku.priceCurrencyCode}")
                EasyLog.log("     订阅期: ${sku.subscriptionPeriod}")
                EasyLog.log("     货币符号检查:")
                EasyLog.log("       - 原始包含$: ${sku.price.contains("$")}")
                EasyLog.log("       - 原始包含NT$: ${sku.price.contains("NT$")}")
                EasyLog.log("       - 修正后包含NT$: ${correctedPrice.contains("NT$")}")
                EasyLog.log("       - 数字部分: ${sku.price.filter { it.isDigit() || it == '.' }}")
            } else {
                EasyLog.log("⚠️ 未找到匹配的商品ID: ${sku.sku}")
            }
        }
        
        if (updatedCount > 0) {
            _products.value = currentProducts
            EasyLog.log("✅ 成功更新了 $updatedCount 个商品的价格信息")
        } else {
            EasyLog.log("❌ 没有商品价格被更新")
            EasyLog.log("可能原因:")
            EasyLog.log("   1. 本地商品ID与Google Play商品ID不匹配")
            EasyLog.log("   2. Google Play返回的商品ID格式不正确")
            EasyLog.log("   3. 本地商品列表为空")
        }
        
        EasyLog.log("=== 商品价格更新结束 ===")
    }
    
    /**
     * 选择商品
     */
    fun selectSku(index: Int) {
        if (index >= 0 && index < _products.value.size) {
            _selectedSkuIndex.value = index
            val selectedProduct = _products.value[index]
            EasyLog.log("选择商品: ${selectedProduct.name} (${selectedProduct.id})")
        }
    }
    
    /**
     * 购买选中的商品
     */
    fun purchaseSelectedSku() {
        val selectedIndex = _selectedSkuIndex.value
        val products = _products.value
        
        if (selectedIndex >= 0 && selectedIndex < products.size) {
            val selectedProduct = products[selectedIndex]
            EasyLog.log("准备购买商品: ${selectedProduct.name} (${selectedProduct.id}) - ${selectedProduct.price}")
            // TODO: 实现购买逻辑，使用 selectedProduct.id
        } else {
            EasyLog.log("无效的商品索引: $selectedIndex")
        }
    }
    
    /**
     * 获取选中的商品
     */
    fun getSelectedProduct(): Product? {
        val selectedIndex = _selectedSkuIndex.value
        val products = _products.value
        
        return if (selectedIndex >= 0 && selectedIndex < products.size) {
            products[selectedIndex]
        } else {
            null
        }
    }
    
    /**
     * 根据货币代码修正货币符号
     */
    private fun correctCurrencySymbol(price: String, currencyCode: String): String {
        val numberPart = price.filter { it.isDigit() || it == '.' }
        
        return when (currencyCode) {
            "TWD" -> "NT$$numberPart"
            "USD" -> "$$numberPart"
            "EUR" -> "€$numberPart"
            "JPY" -> "¥$numberPart"
            "CNY" -> "¥$numberPart"
            "GBP" -> "£$numberPart"
            "KRW" -> "₩$numberPart"
            "SGD" -> "S$$numberPart"
            "HKD" -> "HK$$numberPart"
            else -> price // 如果不知道货币代码，保持原样
        }
    }
    

} 