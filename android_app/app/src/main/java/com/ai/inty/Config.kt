package com.ai.inty

/**
 * 应用配置常量
 */
object Config {
    object TextToImage {
        object Preview {
            /** 预览图宽度 (像素) */
            const val WIDTH = 400
            
            /** 预览图质量 (1-100) */
            const val QUALITY = 60
        }
        object Thumbnail {
            /** 缩略图宽度 (像素) */
            const val WIDTH = 80
            
            /** 缩略图质量 (1-100) */
            const val QUALITY = 60
        }
    }
}