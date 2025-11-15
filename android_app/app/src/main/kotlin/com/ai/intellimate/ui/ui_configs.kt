package com.ai.intellimate.ui

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** 聚合 UI 层常用尺寸、颜色、比例等配置，避免在组件中直接写裸数字。 */
object UiConfigs {

    object Padding {
        val ScreenHorizontal = 16.dp
        val DialogEdge = 24.dp
        val DialogContentHorizontal = 18.dp
        val DialogContentVertical = 16.dp
        val DialogInner = 12.dp
        val TextFieldHorizontal = 8.dp
        val TextFieldVertical = 4.dp
        val TextBlock = 20.dp
    }

    object Spacing {
        val Tiny = 6.dp
        val Small = 8.dp
        val Medium = 12.dp
        val MediumPlus = 16.dp
        val Large = 20.dp
        val HeroGap = 30.dp
        val XLarge = 40.dp
        val VipHeroPlaceholder = 170.dp
    }

    object Size {
        val PrimaryButtonHeight = 50.dp
        val ChatDialogMinHeight = 430.dp
        val ReplyEditorHeight = 168.dp
        val BecomePremiumDialogMinHeight = 300.dp
    }

    object Shape {
        val PrimaryButton = 25.dp
        val Dialog = 12.dp
        val DialogLarge = 20.dp
        val VipDialog = 8.dp
        val SheetTop = 24.dp
        val Input = 8.dp
    }

    object Typography {
        val Title = 22.sp
        val SheetTitle = 20.sp
        val Button = 16.sp
        val ButtonLarge = 18.sp
        val BodyLarge = 16.sp
        val Body = 14.sp
        val Support = 13.sp
        val Caption = 12.sp
    }

    object LineHeight {
        val Button = 22.sp
        val Support = 20.sp
        val SheetTitle = 28.sp
    }

    object Colors {
        val GradientStart = Color(0xFFC122FF)
        val GradientEnd = Color(0xFFFF905D)
        val DialogSurface = Color(0xFF1B0130)
        val VipSecondaryText = Color(0x8CFFFFFF)
        val VipTertiaryText = Color(0x59FFFFFF)
        val InputSurface = Color(0x1A78599A)
        val SheetSurfaceOverlay = Color(0x1AFFFFFF)
        val ReplySheetGradientTop = Color(0xFF322341)
        val ReplySheetGradientBottom = Color(0xFF120E24)
        val PrimaryGradient = listOf(GradientStart, GradientEnd)
        val ReplySheetGradient = listOf(ReplySheetGradientTop, ReplySheetGradientBottom)
    }

    object Fractions {
        const val PrimaryButtonWidth = 0.95f
        const val DialogButtonWidth = 0.85f
        const val TextFieldCornerRadiusRatio = 0.7f
    }

    object Alpha {
        const val DisabledButton = 0.4f
        const val DimmedText = 0.5f
        const val SubtleBorder = 0.2f
    }

    object Limits {
        const val DefaultTextFieldMaxChars = 1000
    }
}
