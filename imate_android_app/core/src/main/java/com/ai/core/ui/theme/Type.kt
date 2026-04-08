package com.ai.core.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// Set of Material typography styles to start with
val HeartTypography =
    Typography(
        titleLarge = TextStyle(fontWeight = FontWeight.Bold, fontSize = 24.sp), // 标题 Title1
        titleMedium = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.Bold),
        titleSmall = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold),
        bodyLarge = TextStyle(fontSize = 14.sp), // 正文 Body
        labelLarge = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.SemiBold),
        labelSmall = TextStyle(fontSize = 10.sp),
        /* Other default text styles to override

        labelSmall = TextStyle(
            fontFamily = FontFamily.Default,
            fontWeight = FontWeight.Medium,
            fontSize = 11.sp,
            lineHeight = 16.sp,
            letterSpacing = 0.5.sp
        )
        */
    )
