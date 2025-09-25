package com.ai.plugins.ext

import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.dsl.ApplicationProductFlavor
import com.android.build.api.dsl.CommonExtension
import com.android.build.api.dsl.ProductFlavor

/**
 * 扩展定义用于区分产品特色、类型不同的参数扩展
 */


@Suppress("EnumEntryName")
internal enum class FlavorDimension {
    contentType
}

// 区分不同构建特性的标记，
@Suppress("EnumEntryName")
internal enum class HeartFlavor(
    val dimension: FlavorDimension,
    val applicationIdSuffix: String? = null
) {
    free(FlavorDimension.contentType),
    premium(FlavorDimension.contentType),

}

/**
 * 配置渠道分包
 */
internal fun configureFlavors(
    commonExtension: CommonExtension<*, *, *, *, *, *>,
    flavorConfigurationBlock: ProductFlavor.(flavor: HeartFlavor) -> Unit = {}
) {
    commonExtension.apply {
        FlavorDimension.values().forEach { flavorDimension ->
            flavorDimensions += flavorDimension.name
        }
        productFlavors {
            HeartFlavor.values().forEach { motoFlavor ->
                create(motoFlavor.name) {
                    dimension = motoFlavor.dimension.name
                    flavorConfigurationBlock(this, motoFlavor)
                    if (this@apply is ApplicationExtension && this is ApplicationProductFlavor) {
                        if (motoFlavor.applicationIdSuffix != null) {
                            applicationIdSuffix = motoFlavor.applicationIdSuffix
                        }
                    }
                }
            }
        }
    }
}
