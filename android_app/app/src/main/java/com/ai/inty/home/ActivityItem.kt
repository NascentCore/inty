// Common constants for ActivityItem
val ACTIVITY_ITEM_HEIGHT = 88.dp
val ACTIVITY_ITEM_AVATAR_SIZE = 56.dp
val ACTIVITY_ITEM_LEFT_PADDING = 16.dp
val ACTIVITY_ITEM_RIGHT_PADDING = 13.dp
val ACTIVITY_ITEM_AVATAR_TO_CONTENT_PADDING = 14.dp
val ACTIVITY_ITEM_NAME_HEIGHT = 22.dp
val ACTIVITY_ITEM_NAME_FONT_SIZE = 15.sp
val ACTIVITY_ITEM_SUBTITLE_HEIGHT = 22.dp
val ACTIVITY_ITEM_SUBTITLE_FONT_SIZE = 14.sp
val ACTIVITY_ITEM_NAME_TO_SUBTITLE_PADDING = 4.dp
val ACTIVITY_ITEM_TIMESTAMP_FONT_SIZE = 12.sp
val ACTIVITY_ITEM_ADDITIONAL_CONTENT_PADDING = 4.dp

/**
 * 通用活动项组件，提取了 ChatHistoryItem 和 FollowingAgentItem 的公共部分
 */
@Composable
fun ActivityItem(
    modifier: Modifier,
    avatarUrl: String,
    name: String,
    subtitle: String,
    rightText: String,
    rightAdditionalContent: @Composable (() -> Unit)? = null,
    placeholderID: Int = R.drawable.app_icon,
) {
    Row(
        modifier = modifier.height(ACTIVITY_ITEM_HEIGHT),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(Modifier.width(ACTIVITY_ITEM_LEFT_PADDING))

        // TODO: 头像，应该重用 chatTopBar 里的 avatar 显示组件
        IntyImage(
            modifier = Modifier.size(ACTIVITY_ITEM_AVATAR_SIZE),
            model = avatarUrl,
            placeholder = painterResource(placeholderID)
        )

        Spacer(Modifier.width(ACTIVITY_ITEM_AVATAR_TO_CONTENT_PADDING))

        // 内容区域
        Column(modifier = Modifier.weight(1f)) {
            Text(
                modifier = Modifier.height(ACTIVITY_ITEM_NAME_HEIGHT),
                text = name,
                fontSize = ACTIVITY_ITEM_NAME_FONT_SIZE,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(Modifier.height(ACTIVITY_ITEM_NAME_TO_SUBTITLE_PADDING))
            Text(
                modifier = Modifier.height(ACTIVITY_ITEM_SUBTITLE_HEIGHT),
                text = subtitle,
                fontSize = ACTIVITY_ITEM_SUBTITLE_FONT_SIZE,
                color = Color.White.copy(0.55f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }

        // 右侧信息
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = rightText,
                fontSize = ACTIVITY_ITEM_TIMESTAMP_FONT_SIZE,
                color = Color.White.copy(0.55f),
            )
            if (rightAdditionalContent != null) {
                Spacer(Modifier.height(ACTIVITY_ITEM_ADDITIONAL_CONTENT_PADDING))
                rightAdditionalContent()
            }
        }

        Spacer(Modifier.width(ACTIVITY_ITEM_RIGHT_PADDING))
    }
}