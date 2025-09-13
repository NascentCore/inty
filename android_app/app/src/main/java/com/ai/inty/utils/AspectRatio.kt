package com.ai.inty.utils

data class AspectRatio(val width: Int, val height: Int)

fun getHeightByWidth(width: Int, aspectRatio: AspectRatio): Int {
    return width * aspectRatio.height / aspectRatio.width
}

fun getWidthByHeight(height: Int, aspectRatio: AspectRatio): Int {
    return height * aspectRatio.width / aspectRatio.height
}

val PORTRAIT_ASPECT_RATIO = AspectRatio(9, 16)
val CHARACTER_CARD_ASPECT_RATIO = AspectRatio(9, 15)
