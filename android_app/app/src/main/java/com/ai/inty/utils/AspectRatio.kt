public data class AspectRatio(val width: Int, val height: Int)

public fun getHeightByWidth(width: Int, aspectRatio: AspectRatio): Int {
    return width * aspectRatio.height / aspectRatio.width
}

public fun getWidthByHeight(height: Int, aspectRatio: AspectRatio): Int {
    return height * aspectRatio.width / aspectRatio.height
}