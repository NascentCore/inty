# Billing Library 8.0.0 Migration Plan

## Overview

Migrate from Google Play Billing Library 7.0.0 to 8.0.0, replacing all deprecated `SkuDetails` API usage with the new `ProductDetails` API.

## Risk Assessment

### High Risk Areas

- **Purchase flow interruption**: Any bugs could prevent users from buying subscriptions
- **Price display errors**: Incorrect price extraction could show wrong prices to users
- **Backend compatibility**: Need to ensure verification flow still works with new API

### Medium Risk Areas

- **Backward compatibility**: Old purchases should still be handled correctly
- **Error handling**: New error codes and responses need proper handling

### Low Risk Areas

- **Connection handling**: BillingClient connection logic remains mostly unchanged
- **Storage layer**: Local persistence unchanged

## Estimated Workload

| Task | Estimated Time | Complexity |

|------|---------------|------------|

| Dependency update | 5 minutes | Low |

| BillingPriceManager refactor | 2-3 hours | High |

| BillingPurchaseManager refactor | 2-3 hours | High |

| BillingModels update | 30 minutes | Low |

| Testing & debugging | 3-4 hours | High |

| **Total** | **8-11 hours** | **High** |

## Breaking Changes in 8.0.0

### Removed APIs (Will Cause Compilation Errors)

1. ✗ `SkuDetails` and `SkuDetailsParams`
2. ✗ `querySkuDetailsAsync()`
3. ✗ `BillingFlowParams.Builder.setSkuDetails()`
4. ✗ `BillingClient.SkuType.SUBS`
5. ✗ `enablePendingPurchases()` (no params version)

### New APIs Required

1. ✓ `ProductDetails` and `QueryProductDetailsParams`
2. ✓ `queryProductDetailsAsync()`
3. ✓ `BillingFlowParams.Builder.setProductDetailsParamsList()`
4. ✓ `ProductType.SUBS`
5. ✓ `enablePendingPurchases(PendingPurchasesParams.newBuilder().build())`

---

## Detailed Migration Steps

### Step 1: Update Gradle Dependencies (5 min)

**File**: `android_app/gradle/libs.versions.toml`

```toml
# Line 69: Change from 7.0.0 to 8.0.0
billingKtx = "8.0.0"
```

**Risk**: Low - Simple version bump

**Testing**: Sync Gradle and check for immediate compilation errors

---

### Step 2: Update BillingRepository Initialization (15 min)

**File**: `BillingRepository.kt` (Line 92-96)

**Current**:

```kotlin
billingClient = BillingClient.newBuilder(context.applicationContext)
    .setListener(this)
    .enablePendingPurchases()  // ❌ Deprecated
    .build()
```

**New**:

```kotlin
import com.android.billingclient.api.PendingPurchasesParams

billingClient = BillingClient.newBuilder(context.applicationContext)
    .setListener(this)
    .enablePendingPurchases(
        PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()
    )
    .build()
```

**Risk**: Low - Well-documented change

**Testing**: Ensure BillingClient connects successfully

---

### Step 3: Refactor BillingPriceManager (2-3 hours)

**File**: `BillingPriceManager.kt` - Complete rewrite required

#### 3.1 Update Imports

```kotlin
// Remove:
import com.android.billingclient.api.SkuDetails
import com.android.billingclient.api.SkuDetailsParams

// Add:
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.ProductDetailsResponseListener
```

#### 3.2 Replace querySkuDetails() Method (Lines 21-126)

**Current Signature**:

```kotlin
fun querySkuDetails(isConnected: Boolean)
```

**Key Changes**:

**Old Product List Building**:

```kotlin
// ❌ Old way (Lines 39-43)
val params = SkuDetailsParams.newBuilder()
    .setSkusList(subscriptionIds)
    .setType(BillingClient.SkuType.SUBS)
    .build()
```

**New Product List Building**:

```kotlin
// ✓ New way
val productList = subscriptionIds.map { productId ->
    QueryProductDetailsParams.Product.newBuilder()
        .setProductId(productId)
        .setProductType(BillingClient.ProductType.SUBS)
        .build()
}

val params = QueryProductDetailsParams.newBuilder()
    .setProductList(productList)
    .build()
```

**Old Async Query**:

```kotlin
// ❌ Old callback (Line 45)
billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
    // ...
}
```

**New Async Query**:

```kotlin
// ✓ New callback
billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsList ->
    // Handle response
}
```

#### 3.3 Update Price Extraction Logic (Lines 128-200)

**Current Method Signature**:

```kotlin
private fun updateLocalPlans(currentPlans: List<VipPlan>, skuDetailsList: List<SkuDetails>)
```

**New Method Signature**:

```kotlin
private fun updateLocalPlans(currentPlans: List<VipPlan>, productDetailsList: List<ProductDetails>)
```

**Price Extraction Changes**:

**Old SkuDetails API** (Lines 134-143):

```kotlin
skuDetails.forEach { skuDetails ->
    val planId = skuDetails.sku  // ❌ Deprecated
    val formattedPrice = skuDetails.price  // ❌ Deprecated
    val currencyCode = skuDetails.priceCurrencyCode  // ❌ Deprecated
    val micros = skuDetails.priceAmountMicros  // ❌ Deprecated
}
```

**New ProductDetails API**:

```kotlin
productDetailsList.forEach { productDetails ->
    val planId = productDetails.productId  // ✓ New
    
    // For subscriptions, get the offer token and pricing info
    val subscriptionOfferDetails = productDetails.subscriptionOfferDetails?.firstOrNull()
    val pricingPhase = subscriptionOfferDetails?.pricingPhases?.pricingPhaseList?.firstOrNull()
    
    val formattedPrice = pricingPhase?.formattedPrice ?: "-"
    val currencyCode = pricingPhase?.priceCurrencyCode ?: ""
    val micros = pricingPhase?.priceAmountMicros ?: 0L
}
```

**Key Complexity**:

- SkuDetails had flat structure
- ProductDetails has nested structure: `subscriptionOfferDetails -> pricingPhases -> pricingPhaseList`
- Need to handle multiple offers and pricing phases (base plans, promotional offers)

**Risk**: High - Complex nested structure, critical for price display

---

### Step 4: Refactor BillingPurchaseManager (2-3 hours)

**File**: `BillingPurchaseManager.kt`

#### 4.1 Update launchBillingFlowInternal() (Lines 401-500)

**Old Product Query** (Lines 403-407):

```kotlin
val params = SkuDetailsParams.newBuilder()
    .setSkusList(listOf(productId))
    .setType(BillingClient.SkuType.SUBS)  // ❌ Deprecated
    .build()

billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
```

**New Product Query**:

```kotlin
val product = QueryProductDetailsParams.Product.newBuilder()
    .setProductId(productId)
    .setProductType(BillingClient.ProductType.SUBS)  // ✓ New
    .build()

val params = QueryProductDetailsParams.newBuilder()
    .setProductList(listOf(product))
    .build()

billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsList ->
```

#### 4.2 Update BillingFlowParams Construction (Lines 434-435)

**Old Flow Params**:

```kotlin
// ❌ Line 434-435
val billingFlowParams = BillingFlowParams.newBuilder()
    .setSkuDetails(skuDetails)
    .build()
```

**New Flow Params**:

```kotlin
// ✓ New way - must specify offer token
val productDetails = productDetailsList.first()
val offerToken = productDetails.subscriptionOfferDetails?.firstOrNull()?.offerToken ?: ""

val productDetailsParams = BillingFlowParams.ProductDetailsParams.newBuilder()
    .setProductDetails(productDetails)
    .setOfferToken(offerToken)  // ⚠️ Required for subscriptions
    .build()

val billingFlowParams = BillingFlowParams.newBuilder()
    .setProductDetailsParamsList(listOf(productDetailsParams))
    .build()
```

**Critical**: Offer token is now required for subscriptions. Missing token will cause purchase failure.

**Risk**: High - Critical for purchase flow

#### 4.3 Update Logging (Lines 417-431)

**Old Property Access**:

```kotlin
skuDetails.sku          // ❌ Changed
skuDetails.title        // ✓ Still works
skuDetails.description  // ✓ Still works
skuDetails.price        // ❌ Changed
skuDetails.priceCurrencyCode  // ❌ Changed
```

**New Property Access**:

```kotlin
productDetails.productId  // ✓ New
productDetails.title
productDetails.description
// Price extraction requires diving into subscriptionOfferDetails
val pricingPhase = productDetails.subscriptionOfferDetails
    ?.firstOrNull()?.pricingPhases?.pricingPhaseList?.firstOrNull()
val price = pricingPhase?.formattedPrice
val currencyCode = pricingPhase?.priceCurrencyCode
```

---

### Step 5: Update Event Models (30 min)

**File**: `BillingModels.kt` (Line 32)

**Current**:

```kotlin
data class SkuDetailsQueryFailed(val code: Int, val message: String) : BillingEvent()
```

**Suggested Rename**:

```kotlin
data class ProductDetailsQueryFailed(val code: Int, val message: String) : BillingEvent()
```

**Impact**: Need to update all references in:

- `BillingPriceManager.kt` (Lines 73, 86, 103, 112, 117)
- Any UI code listening to this event

**Risk**: Low - Simple rename, but requires updating multiple call sites

---

### Step 6: Add Null Safety Handling (1 hour)

The new ProductDetails API has more nullable fields. Add robust null checking:

```kotlin
// Helper extension function to add
fun ProductDetails.getFirstOfferToken(): String? {
    return this.subscriptionOfferDetails?.firstOrNull()?.offerToken
}

fun ProductDetails.getBasePlanPrice(): Triple<String, String, Long>? {
    val pricingPhase = this.subscriptionOfferDetails
        ?.firstOrNull()
        ?.pricingPhases
        ?.pricingPhaseList
        ?.firstOrNull()
    
    return pricingPhase?.let {
        Triple(
            it.formattedPrice,
            it.priceCurrencyCode,
            it.priceAmountMicros
        )
    }
}
```

**Risk**: Medium - Missing null checks could cause crashes

---

### Step 7: Testing Strategy (3-4 hours)

#### 7.1 Unit Testing

- [ ] Test product details query with valid product IDs
- [ ] Test product details query with invalid product IDs
- [ ] Test price extraction from ProductDetails
- [ ] Test offer token extraction
- [ ] Test null handling for missing offers

#### 7.2 Integration Testing

- [ ] Connect to Google Play Billing in debug build
- [ ] Verify prices display correctly in VIP Center
- [ ] Test complete purchase flow with test subscription
- [ ] Verify purchase acknowledgment works
- [ ] Test backend verification still functions
- [ ] Test error handling (network errors, service unavailable)

#### 7.3 Edge Cases

- [ ] Multiple subscription offers (promotional prices)
- [ ] Free trial offers
- [ ] No available offers
- [ ] Billing client disconnection during query
- [ ] App backgrounding during purchase

#### 7.4 Regression Testing

- [ ] Verify existing purchases still recognized
- [ ] Check subscription status updates correctly
- [ ] Ensure local cache/storage still works
- [ ] Test auto-renewal status tracking

---

## Files Requiring Changes

| File | Lines Changed | Complexity | Priority |

|------|--------------|------------|----------|

| `libs.versions.toml` | 1 | Low | P0 |

| `BillingRepository.kt` | 5 | Low | P0 |

| `BillingPriceManager.kt` | ~80 | High | P0 |

| `BillingPurchaseManager.kt` | ~60 | High | P0 |

| `BillingModels.kt` | ~5 | Low | P1 |

| `BillingRemoteManager.kt` | 2 | Low | P1 |

**Total**: ~153 lines changed across 6 files

---

## Rollback Plan

If critical issues arise post-migration:

1. **Immediate**: Revert `billingKtx = "7.0.0"` in version catalog
2. **Revert code changes**: Git revert migration commits
3. **Emergency hotfix**: Release previous version from release branch
4. **Timeline**: Can rollback within 1 hour if caught early

---

## Migration Checklist

### Pre-Migration

- [ ] Create feature branch `billing-8.0-migration`
- [ ] Back up current working code
- [ ] Review Google's official migration guide
- [ ] Set up test Google Play Console products

### During Migration

- [ ] Update Gradle dependency
- [ ] Update BillingRepository initialization
- [ ] Refactor BillingPriceManager
- [ ] Refactor BillingPurchaseManager
- [ ] Update BillingModels
- [ ] Add null safety extensions
- [ ] Update all import statements

### Post-Migration

- [ ] Run unit tests
- [ ] Test on debug build with real billing
- [ ] Test complete purchase flow
- [ ] Verify backend integration
- [ ] Test on multiple devices/Android versions
- [ ] Check logs for any warnings
- [ ] Performance testing (no regressions)

### Release Preparation

- [ ] Update CHANGELOG.md
- [ ] Document any new error codes
- [ ] Prepare rollback instructions
- [ ] Stage release to internal testing track
- [ ] Monitor crash reports closely

---

## Key Success Criteria

1. ✓ All compilation errors resolved
2. ✓ Prices display correctly in UI
3. ✓ Purchase flow completes successfully
4. ✓ Backend verification unchanged
5. ✓ No new crashes in billing code
6. ✓ Existing subscriptions still work
7. ✓ Test purchases work in debug builds

---

## Estimated Timeline

| Phase | Duration | Can Parallelize |

|-------|----------|----------------|

| Code changes | 5-6 hours | No |

| Testing | 3-4 hours | Partially |

| Bug fixes | 1-2 hours | No |

| **Total** | **9-12 hours** | - |

**Recommendation**: Allocate 2 full working days for this migration to account for unexpected issues.

---

## Additional Notes

- **Compatibility**: Billing Library 8.0.0 requires Android Gradle Plugin 7.0+
- **Minimum SDK**: No change (still supports Android 4.4+)
- **Breaking Change**: This is a major API redesign, not just a simple upgrade
- **Google Recommendation**: All apps should migrate by Q2 2025
- **Alternative**: Stay on 7.0.0 which is still supported but deprecated