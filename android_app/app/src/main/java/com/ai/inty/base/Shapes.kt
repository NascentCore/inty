package com.ai.inty.base

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp



@Composable
fun RedDot() {
    Box(
        modifier = Modifier
            .size(8.dp)
            .background(
                color = Color.Red,  // 红色填充[4](@ref)
                shape = CircleShape  // 圆形裁剪[1,6](@ref)
            )
    )
}
