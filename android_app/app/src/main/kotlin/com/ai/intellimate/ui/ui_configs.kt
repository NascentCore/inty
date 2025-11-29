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
        val GoogleLoginButton = 18.sp
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

    object Urls {
        const val WhatsAppGroupInvite = "https://chat.whatsapp.com/Cw1ZM46InipFHel3ws5ria"
        const val DiscordInvite = "https://discord.gg/xbJJ9NBdJT"
        const val HelpCenter =
            "https://www.notion.so/IntelliMate-Help-Center-2b88c199b74b808a985bcaa64e36c322"
    }

    object Explore {
        /** 页面大小 - 统一管理，确保启动预加载和分页逻辑一致 */
        const val PAGE_SIZE = 8

        /** 预取距离 - 提前加载下一页 设置为8，意味着当还有8个项目时就开始预加载下一页 对于20个/页，相当于在显示到第12个时就开始加载下一页 */
        const val PREFETCH_DISTANCE = 16

        /** 是否启用占位符 - 禁用占位符，提高性能 */
        const val ENABLE_PLACEHOLDERS = false

        /** 最大缓存页数 - 最大缓存3页数据 */
        const val MAX_CACHE_PAGES = 100

        /** 初始页码 */
        const val INITIAL_PAGE = 1

        /** Explore页面滚动 - 初始速度缩放，用于整体放缓或加速手势 */
        const val SCROLL_INITIAL_VELOCITY_MULTIPLIER = 0.6f

        /** Explore页面滚动 - 触发滑动的最小速度，避免轻微抖动 */
        const val SCROLL_MIN_FLING_VELOCITY = 80f

        /** Explore页面滚动 - 限制最大速度，防止 fling 过猛 */
        const val SCROLL_MAX_FLING_VELOCITY = 12000f

        /** Explore页面滚动 - 减速度因子，>1 表示更快停下，<1 表示惯性更强 */
        const val SCROLL_DECELERATION_MULTIPLIER = 1.0f

        /** Explore页面滚动 - 每次手势允许的最大即时位移 */
        const val SCROLL_DELTA_THRESHOLD = 500f
    }

    object BottomBar {
        val Height = 64.dp
        val TabIconSize = 24.dp
        val TabIconLabelSpacing = (-6).dp
    }

    object MePage {
        object TopIconsRow {
            val Size = 24.dp
            val Spacing = 8.dp
            val RightPadding = 16.dp
        }
        val TopSpacerOffset = 28.dp

        // 顶部折叠效果参数
        val HeaderMaxHeight = 280.dp
        val HeaderMinHeight = 80.dp

        // Avatar
        val AvatarFullSize = 120.dp
        val AvatarPadding = 4.dp
        val AvatarToNicknameSpacing = 19.dp

        // Spacing
        val SectionSpacing = 24.dp
        val BottomSpacing = 8.dp

        // Edit button
        val EditButtonSize = 40.dp

        // VIP Banner
        val VipBannerHeight = 120.dp

        // Agent card
        val AgentCardWidth = 165.dp
        val AgentCardHeight = 220.dp
        val AgentCardCornerRadius = 12.dp
        val AgentCardPadding = 8.dp
        val AgentCardMenuButtonSize = 28.dp
        val AgentCardMenuIconSize = 20.dp
        val AgentCardMenuButtonCornerRadius = 4.dp
        val AgentCardTextSpacing = 4.dp

        // Grid
        val GridHorizontalSpacing = 13.dp
        val GridVerticalSpacing = 16.dp
        val GridHorizontalPadding = 16.dp
        val GridContentBottomPadding = 100.dp

        // Empty state
        val EmptyStateTopSpacing = 48.dp
        val EmptyStateBottomSpacing = 16.dp
        val EmptyStateContentSpacing = 10.dp

        // Intro section
        val IntroSectionCollapsedHeight = 40.dp
        val IntroSectionExpandedHeight = 60.dp
    }

    object ChatMessagePane {
        val PaddingHorizontal = 12.dp
        val PaddingVertical = 13.dp
        const val WIDTH_RATIO = 0.9f
    }
}
