package ai.sxwl.android.design.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// Set of Material typography styles to start with
val HeartTypography =
    Typography(
        titleLarge =
            TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Bold,
                fontSize = 24.sp,
            ),
        titleMedium = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.Bold),
        titleSmall = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold),
        bodyLarge = TextStyle(fontSize = 14.sp),
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
