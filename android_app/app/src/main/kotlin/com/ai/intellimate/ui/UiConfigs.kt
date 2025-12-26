package com.ai.intellimate.ui

import ai.sxwl.android.data.store.IntySetting
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.settings.RemixButtonVisibilityManager

/** 聚合 UI 层常用尺寸、颜色、比例等配置，避免在组件中直接写裸数字。 */
object UiConfigs {
    /** 内边距配置 - 适用于屏幕、对话框、输入框等组件的内边距设置 */
    object Padding {
        /** 屏幕水平方向内边距 */
        val ScreenHorizontal = 16.dp

        /** 对话框边缘内边距 */
        val DialogEdge = 24.dp

        /** 对话框内容水平内边距 */
        val DialogContentHorizontal = 18.dp

        /** 对话框内容垂直内边距 */
        val DialogContentVertical = 16.dp

        /** 对话框内部内边距 */
        val DialogInner = 12.dp

        /** 文本输入框水平内边距 */
        val TextFieldHorizontal = 8.dp

        /** 文本输入框垂直内边距 */
        val TextFieldVertical = 4.dp

        /** 文本块内边距 */
        val TextBlock = 20.dp
    }

    /** 间距配置 - 适用于组件之间的间距设置，提供不同大小的间距选项 */
    object Spacing {
        /** 极小间距 */
        val Tiny = 6.dp

        /** 小间距 */
        val Small = 8.dp

        /** 中等间距 */
        val Medium = 12.dp

        /** 中等偏大间距 */
        val MediumPlus = 16.dp

        /** 大间距 */
        val Large = 20.dp

        /** 主要区域间距 */
        val HeroGap = 30.dp

        /** 超大间距 */
        val XLarge = 40.dp

        /** VIP 主要区域占位符高度 */
        val VipHeroPlaceholder = 170.dp
    }

    /** 尺寸配置 - 适用于按钮、对话框、编辑器等组件的高度和宽度设置 */
    object Size {
        /** 主要按钮高度 */
        val PrimaryButtonHeight = 50.dp

        /** 聊天对话框最小高度 */
        val ChatDialogMinHeight = 430.dp

        /** 回复编辑器高度 */
        val ReplyEditorHeight = 168.dp

        /** 成为会员对话框最小高度 */
        val BecomePremiumDialogMinHeight = 300.dp
    }

    /** 形状配置 - 适用于按钮、对话框、输入框等组件的圆角半径设置 */
    object Shape {
        /** 主要按钮圆角半径 */
        val PrimaryButton = 25.dp

        /** 对话框圆角半径 */
        val Dialog = 12.dp

        /** 大对话框圆角半径 */
        val DialogLarge = 20.dp

        /** VIP 对话框圆角半径 */
        val VipDialog = 8.dp

        /** 底部表单顶部圆角半径 */
        val SheetTop = 24.dp

        /** 输入框圆角半径 */
        val Input = 8.dp
    }

    /** 字体配置 - 适用于标题、按钮、正文等文本的字体大小设置 */
    object Typography {
        /** 标题字体大小 */
        val Title = 22.sp

        /** 底部表单标题字体大小 */
        val SheetTitle = 20.sp

        /** 按钮字体大小 */
        val Button = 16.sp

        /** 大按钮字体大小 */
        val ButtonLarge = 18.sp

        /** Google 登录按钮字体大小 */
        val GoogleLoginButton = 18.sp

        /** 大正文字体大小 */
        val BodyLarge = 16.sp

        /** 正文字体大小 */
        val Body = 14.sp

        /** 辅助文字字体大小 */
        val Support = 13.sp

        /** 说明文字字体大小 */
        val Caption = 12.sp
    }

    /** 行高配置 - 适用于按钮、辅助文字、表单标题等文本的行高设置 */
    object LineHeight {
        /** 按钮行高 */
        val Button = 22.sp

        /** 辅助文字行高 */
        val Support = 20.sp

        /** 底部表单标题行高 */
        val SheetTitle = 28.sp
    }

    /** 颜色配置 - 适用于渐变、对话框、VIP 文字、输入框等组件的颜色设置 */
    object Colors {
        /** 渐变起始颜色 */
        val GradientStart = Color(0xFFC122FF)

        /** 渐变结束颜色 */
        val GradientEnd = Color(0xFFFF905D)

        /** 对话框背景颜色 */
        val DialogSurface = Color(0xFF1B0130)

        /** VIP 次要文字颜色 */
        val VipSecondaryText = Color(0x8CFFFFFF)

        /** VIP 第三级文字颜色 */
        val VipTertiaryText = Color(0x59FFFFFF)

        /** 输入框背景颜色 */
        val InputSurface = Color(0x1A78599A)

        /** 底部表单表面遮罩颜色 */
        val SheetSurfaceOverlay = Color(0x1AFFFFFF)

        /** 回复表单渐变顶部颜色 */
        val ReplySheetGradientTop = Color(0xFF322341)

        /** 回复表单渐变底部颜色 */
        val ReplySheetGradientBottom = Color(0xFF120E24)

        /** 主要渐变颜色列表 */
        val PrimaryGradient = listOf(GradientStart, GradientEnd)

        /** 回复表单渐变颜色列表 */
        val ReplySheetGradient = listOf(ReplySheetGradientTop, ReplySheetGradientBottom)
    }

    /** 头像生成页面配置 - 适用于 AvatarGenerateActivity 的风格选择等模块 */
    object AvatarGenerate {
        object StyleSelector {
            /** 风格卡片宽度 */
            val CardWidth = 170.dp

            /** 风格卡片高度 */
            val CardHeight = 72.dp

            /** 风格卡片圆角 */
            val CardCornerRadius = 12.dp

            /** 风格卡片边框宽度 */
            val CardBorderWidth = 1.dp
        }
    }

    /** 创建角色页面配置 - 适用于 CreateRoleActivity 的表单与区块布局 */
    object CreateRole {
        /** 视觉形象区域配置 - 头像预览与编辑入口 */
        object VisualAppearance {
            /**
             * 预览框宽高比（width / height）。
             *
             * 默认 9/16，即竖屏比例。
             */
            const val ASPECT_RATIO = 9f / 16f

            /** 空状态内容内边距（用于保持按钮区域不拥挤） */
            val EmptyStateInnerPadding = 16.dp

            /** 预览框右上角“Crop”浮层按钮的内边距（水平/垂直保持一致） */
            val FaceEditPillPadding = 12.dp

            /** 空状态按钮内容内边距（水平/垂直保持一致） */
            val EmptyStateButtonContentPadding = 8.dp

            /** 头像上传区域垂直内边距 */
            val SectionVerticalPadding = 8.dp
        }

        /** 性别选择区域配置 */
        object GenderSelection {
            /** 性别选择按钮字体大小 */
            val ButtonFontSize = 18.sp
        }
    }

    /** 比例配置 - 适用于按钮、输入框等组件相对于父容器的宽度或圆角半径比例设置 */
    object Fractions {
        /** 主要按钮宽度比例（相对于父容器） */
        const val PrimaryButtonWidth = 0.95f

        /** 对话框按钮宽度比例（相对于父容器） */
        const val DialogButtonWidth = 0.85f

        /** 文本输入框圆角半径比例 */
        const val TextFieldCornerRadiusRatio = 0.7f
    }

    /** 透明度配置 - 适用于禁用按钮、变暗文字、边框等组件的透明度设置 */
    object Alpha {
        /** 禁用按钮透明度 */
        const val DisabledButton = 0.4f

        /** 变暗文字透明度 */
        const val DimmedText = 0.5f

        /** 次要文字透明度 */
        const val SecondaryText = 0.7f

        /** 细微边框透明度 */
        const val SubtleBorder = 0.2f
    }

    /** 限制配置 - 适用于输入框等组件的字符数限制设置 */
    object Limits {
        /** 默认文本输入框最大字符数 */
        const val DefaultTextFieldMaxChars = 1000
    }

    /** URL 配置 - 适用于外部链接，如社交媒体邀请链接、帮助中心等 */
    object Urls {
        /** WhatsApp 群组邀请链接 */
        const val WhatsAppGroupInvite =
            "https://chat.whatsapp.com/DpMVkOQTWOdJfZnnVqiXm8?mode=hqrt3"

        /** Discord 邀请链接 */
        const val DiscordInvite = "https://discord.gg/xbJJ9NBdJT"

        /** 帮助中心链接 */
        const val HelpCenter =
            "https://www.notion.so/IntelliMate-Help-Center-2b88c199b74b808a985bcaa64e36c322"

        /**
         * 语音通话WebSocket URL
         * 注意：此URL需要根据实际后端服务地址配置
         * 格式：wss://domain.com/voice/ws?agentId={agentId}
         */
        fun getVoiceCallWebSocketUrl(agentId: String): String {
            // TODO: 替换为实际的WebSocket服务器地址
            return "wss://dev.inty.sxwl.ai/api/v1/live-chat/$agentId?token=${IntySetting.getCurToken()}"
        }
    }

    /** 语音通话配置 - 适用于实时语音通话的队列大小、缓冲区等设置 */
    object VoiceCall {
        /** 播放队列最大大小（音频数据包数量） - 约3秒的音频数据（24kHz，16bit，单声道）
         *  增大队列以提高播放流畅度，减少因网络波动导致的卡顿 */
        const val MAX_PLAYBACK_QUEUE_SIZE = 75

        /** 发送队列最大大小（音频数据包数量） - 约1秒的音频数据（16kHz，16bit，单声道） */
        const val MAX_SEND_QUEUE_SIZE = 30

        /** 队列大小警告阈值（百分比） - 当队列使用率超过此值时记录警告日志 */
        const val QUEUE_WARNING_THRESHOLD = 0.8f // 80%
    }

    /** Explore 页面配置 - 适用于发现页面的分页、预加载、滚动行为等设置 */
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

    /** 底部导航栏配置 - 适用于底部导航栏的高度、图标大小、间距等设置 */
    object BottomBar {
        /** 底部导航栏高度 */
        val Height = 66.dp

        /** 标签图标大小 */
        val TabIconSize = 23.dp

        /** 标签图标与文字之间的间距 */
        val TabIconLabelSpacing = (-8).dp

        /** 距离屏幕底部间距 */
        val BottomSpacing = 6.dp
    }

    /** 个人页面配置 - 适用于个人资料页面的头像、卡片、网格、空状态等组件的尺寸和间距设置 */
    object MePage {
        /** 顶部图标行配置 - 适用于个人页面顶部图标行的图标大小、间距和内边距设置 */
        object TopIconsRow {
            /** 顶部图标行图标大小 */
            val Size = 28.dp

            /** 顶部图标行图标间距 */
            val Spacing = 8.dp

            /** 顶部图标行右侧内边距 */
            val RightPadding = 16.dp
        }

        /** 顶部间距偏移量 */
        val TopSpacerOffset = 56.dp

        /** 顶部折叠效果 - 头部最大高度 */
        val HeaderMaxHeight = 280.dp

        /** 顶部折叠效果 - 头部最小高度 */
        val HeaderMinHeight = 80.dp

        /** 头像完整大小 */
        val AvatarFullSize = 90.dp

        /** 头像内边距 */
        val AvatarPadding = 4.dp

        /** 头像到昵称之间的间距 */
        val AvatarToNicknameSpacing = 24.dp

        /**
         * 个人页 Header 中名字+简介整体上移的偏移量。
         *
         * 预期视觉效果：名字与 persona description 更贴近头像上方区域，避免整体偏下。
         */
        val ProfileNameBlockYOffset = (-6).dp

        /** 名字与 persona description 之间的垂直间距 */
        val ProfileNameToDescriptionSpacing = Spacing.Tiny / 3

        /** 区域之间的间距 */
        val SectionSpacing = 16.dp

        /** 底部间距 */
        val BottomSpacing = 8.dp

        /** 编辑按钮大小 */
        val EditButtonSize = 40.dp

        /** VIP 横幅高度 */
        val VipBannerHeight = 140.dp

        /** 角色卡片宽度 */
        val AgentCardWidth = 165.dp

        /** 角色卡片高度 */
        val AgentCardHeight = 220.dp

        /** 角色卡片圆角半径 */
        val AgentCardCornerRadius = 12.dp

        /** 角色卡片内边距 */
        val AgentCardPadding = 8.dp

        /** 角色卡片菜单按钮大小 */
        val AgentCardMenuButtonSize = 28.dp

        /** 角色卡片菜单图标大小 */
        val AgentCardMenuIconSize = 20.dp

        /** 角色卡片菜单按钮圆角半径 */
        val AgentCardMenuButtonCornerRadius = 4.dp

        /** 角色卡片文字间距 */
        val AgentCardTextSpacing = 4.dp

        /** 网格水平间距 */
        val GridHorizontalSpacing = 13.dp

        /** 网格垂直间距 */
        val GridVerticalSpacing = 16.dp

        /** 网格水平内边距 */
        val GridHorizontalPadding = 16.dp

        /** 网格内容底部内边距 */
        val GridContentBottomPadding = 100.dp

        /** 空状态顶部间距 */
        val EmptyStateTopSpacing = 48.dp

        /** 空状态底部间距 */
        val EmptyStateBottomSpacing = 16.dp

        /** 空状态内容间距 */
        val EmptyStateContentSpacing = 10.dp

        /** 介绍区域折叠时高度 */
        val IntroSectionCollapsedHeight = 40.dp

        /** 介绍区域展开时高度 */
        val IntroSectionExpandedHeight = 60.dp

        /** Vibe 模式配置 - 适用于个人页面中 Vibe 模式横幅的尺寸和样式设置 */
        object VibeMode {
            /** Vibe 模式横幅高度 */
            val BannerHeight = 92.dp

            /** Vibe 模式圆角半径 */
            val CornerRadius = 20.dp

            /** Vibe 模式边框宽度 */
            val BorderWidth = 1.dp

            /** Vibe 模式内部内边距 */
            val InnerPadding = 18.dp

            /** Vibe 模式内容间距 */
            val ContentSpacing = 12.dp
        }
    }

    /** 聊天消息面板配置 - 适用于聊天页面中消息面板的内边距、消息宽度比例、时间戳、音频播放器等设置 */
    object ChatMessagePane {
        /** 聊天消息面板水平内边距 */
        val PaddingHorizontal = 12.dp

        /** 聊天消息面板垂直内边距 */
        val PaddingVertical = 13.dp

        /** AI 消息宽度比例（相对于父容器） */
        const val AI_WIDTH_RATIO = 0.9f

        /** 用户消息宽度比例（相对于父容器） */
        const val USER_WIDTH_RATIO = 0.3f

        /** 用户消息最大宽度 */
        val UserMessageMaxWidth = 300.dp

        /** 时间戳字体大小 */
        val TimestampFontSize = 10.sp

        /** 音频播放器到时间戳之间的间距 */
        val AudioPlayerToTimestampSpacing = 8.dp

        /** 音频播放器最小宽度 */
        val AudioPlayerMinWidth = 38.dp

        /** 消息操作按钮图标大小 - 适用于点赞、点踩、召回、图片生成等操作按钮 */
        val ActionButtonIconSize = 24.dp

        /** 消息操作按钮之间的间距 */
        val ActionButtonSpacing = 12.dp
    }

    /** 聊天顶部栏配置 - 适用于聊天页面顶部栏的尺寸、间距、字体等设置 */
    object ChatTopBar {
        /** 头像大小 */
        val AvatarSize = 40.dp

        /** 头像内边距 */
        val AvatarPadding = 3.dp

        /** 顶部栏圆角半径 */
        val CornerRadius = 28.dp

        /** 顶部栏背景颜色 */
        val BackgroundColor = Color(33, 0, 0, 77)

        /** 返回按钮图标大小 */
        val BackButtonIconSize = 24.dp

        /** 更多按钮图标大小 */
        val MoreButtonIconSize = 20.dp

        /** 返回按钮与头像之间的间距 */
        val BackButtonToAvatarSpacing = 8.dp

        /** 头像与内容之间的间距 */
        val AvatarToContentSpacing = 6.dp

        /** 能量图标大小 */
        val EnergyIconSize = 14.dp

        /** 能量图标与文字之间的间距 */
        val EnergyIconToTextSpacing = 4.dp

        /** 能量点数与名称之间的间距 */
        val EnergyPointsToNameSpacing = 2.dp

        /** 内容区域右侧内边距 */
        val ContentRightPadding = 16.dp

        /** 名称字体大小 */
        val NameFontSize = 14.sp

        /** 能量点数字体大小 */
        val EnergyPointsFontSize = 10.sp

        /** 收藏按钮大小 */
        val FavoriteButtonSize = 36.dp

        /** 收藏图标大小 */
        val FavoriteIconSize = 18.dp

        /** 操作按钮之间的间距 */
        val ActionButtonSpacing = 8.dp

        /** 操作按钮容器透明度 */
        const val ActionButtonContainerAlpha = 0.35f

        /** 收藏按钮激活状态颜色（粉色） */
        val FavoriteActiveTint = Color(0xFFFF5A8A)

        /** 收藏按钮未激活状态颜色（白色） */
        val FavoriteInactiveTint = Color.White
    }

    /** 聊天页面配置 - 适用于聊天页面的功能开关，如 Remix 按钮可见性等 */
    object ChatPage {
        /** 是否显示订阅按钮 */
        const val showSubscriptionButton = false

        /** 消息列表非全屏模式下，上部分空白区占比 */
        const val chatListBlankZone = 1f / 3f

        object KeepTalkingButton {
            /** Keep Talking 悬浮按钮宽度（用于扩大点击热区） */
            val width = 50.dp
            val padding = 4.dp
            val iconSize = 24.dp
        }

        /** 聊天输入框配置 - 适用于聊天输入框的尺寸、间距等设置 */
        object ChatInput {
            /** 聊天输入框底部空白边距 - 输入框与键盘或更多面板之间的间距 */
            val BottomSpacerHeight = 6.dp
        }

        /** 聊天气泡配置 - 适用于聊天消息气泡的装饰、样式等设置 */
        object ChatBubble {
            /** 圣诞装饰图标大小 - 适用于圣诞树、草莓、糖果等装饰图标 */
            val ChristMasTreeSize = 48.dp
            val CherrySize = 40.dp
            val SnowDecorationSize = 80.dp
            val ChritsmasDecorationSize = 60.dp
        }

        @Composable
        fun enableRemix(): Boolean {
            val visibilityState by RemixButtonVisibilityManager.visibility.collectAsState()
            LaunchedEffect(Unit) {
                if (visibilityState == null) {
                    val current = RemixButtonVisibilityManager.getCurrentVisibility()
                    RemixButtonVisibilityManager.updateVisibility(current)
                }
            }
            return visibilityState ?: RemixButtonVisibilityManager.getCurrentVisibility()
        }

        /** 滚动到底部按钮配置 - 适用于聊天页面中滚动到底部按钮的尺寸、样式、位置等设置 */
        object ScrollToBottomButton {
            /** 左上角圆角半径 */
            val CornerRadiusTopStart = 20.dp

            /** 左下角圆角半径 */
            val CornerRadiusBottomStart = 20.dp

            /** 边框宽度 */
            val BorderWidth = 1.dp

            /** 边框渐变起始颜色透明度（启用状态） */
            const val BorderGradientStartAlpha = 0.7f

            /** 边框渐变起始颜色透明度（禁用状态） */
            const val BorderGradientStartAlphaDisabled = 0.3f

            /** 边框渐变结束颜色透明度 */
            const val BorderGradientEndAlpha = 0.2f

            /** 背景颜色透明度 */
            const val BackgroundAlpha = 0.6f

            /** 禁用状态整体透明度 */
            const val DisabledAlpha = 0.5f

            /** 按钮内部内边距 */
            val InnerPadding = 4.dp

            /** 图标大小 */
            val IconSize = 30.dp

            /** 按钮整体大小（圆形按钮的直径） */
            val ButtonSize = IconSize + InnerPadding * 2 + BorderWidth * 2

            /** 右侧内边距 */
            val RightPadding = 16.dp

            /** 位于 KeepTalkingFloatingButton 上方的间距 */
            val BottomOffsetAboveKeepTalking = 60.dp
        }

        /** 聊天页“滚动到开始/滚动到最新”双按钮的布局配置 */
        object ScrollToHistoryButtons {
            /** 两个圆形按钮之间的垂直间距 */
            val VerticalSpacing = 12.dp
        }

        /** 相册配置 - 适用于角色相册页面的列数等设置 */
        object PhotoAlbum {
            /** 预览区域配置 - 适用于角色信息页面中的图片预览区域 */
            object Preview {
                /** 预览区域列数 */
                const val COLUMN_COUNT = 4

                /** 标题字体大小 */
                val TitleFontSize = 16.sp

                /** "See All" 按钮字体大小 */
                val SeeAllFontSize = 14.sp

                /** "See All" 按钮文字透明度 */
                const val SeeAllTextAlpha = 0.85f

                /** 图片卡片背景透明度 */
                const val ImageCardBackgroundAlpha = 0.08f

                /** 背景状态指示器大小 */
                val BackgroundIndicatorSize = 16.dp

                /** 背景状态指示器内边距 */
                val BackgroundIndicatorPadding = 8.dp

                /** 背景状态指示器颜色 */
                val BackgroundIndicatorColor = ai.sxwl.android.design.theme.AppColors.Green500
            }

            /** 全屏相册页面配置 - 适用于角色相册全屏页面 */
            object All {
                /** 相册网格列数 */
                const val COLUMN_COUNT = 2

                /** TopBar 标题字体大小 */
                val TopBarTitleFontSize = 18.sp

                /** 返回按钮图标大小 */
                val BackButtonIconSize = 24.dp

                /** 空状态文字字体大小 */
                val EmptyStateFontSize = 14.sp

                /** 空状态文字透明度 */
                const val EmptyStateTextAlpha = 0.7f

                /** 网格内容垂直内边距 */
                val GridContentVerticalPadding = 16.dp

                /** 图片项按钮区域顶部间距 */
                val ImageItemButtonTopPadding = 8.dp

                /** 图片项按钮图标大小 */
                val ImageItemButtonIconSize = 20.dp

                /** 图片项按钮文字字体大小 */
                val ImageItemButtonTextFontSize = 12.sp

                /** 图片项按钮文字透明度 */
                const val ImageItemButtonTextAlpha = 0.85f

                /** 图片卡片背景透明度 */
                const val ImageCardBackgroundAlpha = 0.08f

                /** 背景状态指示器颜色 */
                val BackgroundIndicatorColor = ai.sxwl.android.design.theme.AppColors.Green500
            }
        }

        /** 通用悬浮圆形滚动按钮样式（用于 Chat/Explore 等页面复用） */
        object FloatingScrollButton {
            /** 边框宽度 */
            val BorderWidth = 1.dp

            /** 边框渐变起始颜色透明度（启用状态） */
            const val BorderGradientStartAlpha = 0.7f

            /** 边框渐变起始颜色透明度（禁用状态） */
            const val BorderGradientStartAlphaDisabled = 0.3f

            /** 边框渐变结束颜色透明度 */
            const val BorderGradientEndAlpha = 0.2f

            /** 背景颜色透明度 */
            const val BackgroundAlpha = 0.6f

            /** 禁用状态整体透明度 */
            const val DisabledAlpha = 0.5f

            /** 按钮内部内边距 */
            val InnerPadding = 4.dp

            /** 图标大小 */
            val IconSize = 30.dp

            /** 按钮整体大小（圆形按钮的直径） */
            val ButtonSize = IconSize + InnerPadding * 2 + BorderWidth * 2

            /** 右侧内边距（用于靠右悬浮布局） */
            val RightPadding = 16.dp
        }
    }

    object CharacterIntroduction {
        const val TITLE_FONT_SIZE = 16
    }

    /** 角色资料配置 - 适用于角色资料页面的背景视频播放次数、CDN 图片质量和宽度等设置 */
    object CharacterProfile {
        /** 页面切换时的播放次数 */
        const val VIDEO_FIRST_PLAY_COUNT = 2

        /** 消息加载时的播放次数 */
        const val VIDEO_MESSAGE_PLAY_COUNT = 1

        /** CDN 静态背景图片质量（0-100） */
        const val CDN_IMAGE_QUALITY = 80

        /** CDN 静态背景图片宽度（像素） */
        const val CDN_STATIC_BACKGROUND_WIDTH = 1080
    }

    /** 角色画廊配置 - 适用于角色信息页面中 AI 生成图片画廊的间距、尺寸、CDN 图片参数等设置 */
    object CharacterGallery {
        /** 画廊区域之间的间距 */
        val SectionSpacing = 12.dp

        /** 标题与描述之间的间距 */
        val SectionTitleSpacing = 4.dp

        /** 画廊图片之间的水平间距 */
        val ImageSpacing = 12.dp

        /** 画廊图片的宽度 */
        val ImageWidth = 140.dp

        /** 画廊图片的圆角半径 */
        val ImageCornerRadius = 14.dp

        /** 画廊区域底部的内边距 */
        val SectionBottomPadding = 8.dp

        /** CDN 画廊图片宽度（像素） */
        const val CDN_IMAGE_WIDTH = 480

        /** CDN 画廊图片质量（0-100） */
        const val CDN_IMAGE_QUALITY = 70
    }

    /** 反馈对话框配置 - 适用于反馈请求对话框的随机阈值等设置 */
    object FeedbackDialog {
        /** 消息数阈值 - 当前使用期内（app 打开未退出/未后台挂起）发送消息数每达到此阈值时显示对话框 */
        const val SESSION_MESSAGES_COUNT_THRESHOLD = 30
        /** 最小显示间隔（毫秒）- 防止频繁显示对话框，至少间隔此时间才能再次显示 */
        const val MIN_SHOW_INTERVAL_MS = 3 * 24 * 60 * 60 * 1000L // 3天
    }

    /** 排行榜配置 - 适用于 Boost 排行榜页面的间距、尺寸、颜色等设置 */
    object LeaderBoard {
        /** 页面水平内边距 - 与 Explore 页面角色卡片保持一致 */
        val HorizontalPadding = 16.dp

        /** 页面垂直内边距 */
        val VerticalPadding = 8.dp

        /** 状态芯片与标题之间的间距 */
        val StatusChipToTitleSpacing = 24.dp

        /** 标题底部内边距 */
        val TitleBottomPadding = 12.dp

        /** 状态芯片与列表之间的间距 */
        val StatusChipToListSpacing = 24.dp

        /** 空状态卡片圆角半径 */
        val EmptyStateCardCornerRadius = 16.dp

        /** 空状态卡片内边距 */
        val EmptyStateCardPadding = 24.dp

        /** 列表项之间的垂直间距 */
        val ListItemSpacing = 12.dp

        /** 列表底部间距 */
        val ListBottomSpacing = 32.dp

        /** 排行榜行卡片圆角半径 */
        val RowCardCornerRadius = 16.dp

        /** 排行榜行卡片内边距 */
        val RowCardPadding = 16.dp

        /** 排名与头像之间的间距 */
        val RankToAvatarSpacing = 12.dp

        /** 头像尺寸 */
        val AvatarSize = 48.dp

        /** 头像与名称之间的间距 */
        val AvatarToNameSpacing = 12.dp

        /** 名称区域与按钮区域之间的间距 */
        val NameToButtonSpacing = 12.dp

        /** 按钮之间的水平间距 */
        val ButtonSpacing = 12.dp

        /** 行之间的分隔间距 */
        val RowDividerSpacing = 4.dp

        /** 趋势标签水平内边距 */
        val TrendPillHorizontalPadding = 12.dp

        /** 趋势标签垂直内边距 */
        val TrendPillVerticalPadding = 4.dp

        /** 趋势图标尺寸 */
        val TrendIconSize = 14.dp

        /** 趋势图标与文字之间的间距 */
        val TrendIconToTextSpacing = 4.dp

        /** Top 10 按钮右侧间距 - 与 Explore 页面角色卡片保持一致 */
        val Top10ButtonRightPadding = 16.dp
    }
}
