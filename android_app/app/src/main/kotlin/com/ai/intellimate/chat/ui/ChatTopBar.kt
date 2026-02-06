package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.AppColors
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material.icons.rounded.EnergySavingsLeaf
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.xb.helper.AgentStore
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.launch

private const val VIP_TAG = "vip"

/** 统一清洗标签，避免大小写与前缀差异影响判断结果。 */
private fun normalizeTag(tag: String): String {
    val trimmed = tag.trim()
    if (trimmed.isEmpty()) return ""
    return trimmed.removePrefix("#").lowercase()
}

/** 判断角色是否包含 VIP 标签。 */
private fun isVipAgent(tags: List<String?>?): Boolean {
    if (tags.isNullOrEmpty()) return false
    return tags.filterNotNull().any { normalizeTag(it) == VIP_TAG }
}

/**
 * 收藏按钮组件
 *
 * 使用场景：
 * - 聊天页面顶部栏中的收藏按钮
 * - 与探索页角色卡片保持一致的行为：未收藏时显示空心图标，收藏后显示粉色实心图标
 *
 * 可配置项：
 * - agentId: 角色ID，用于获取和设置收藏状态
 * - modifier: 可选的修饰符
 * - containerColor: 按钮容器背景色（默认透明）
 */
@Composable
private fun FavoriteButton(
    agentId: String,
    modifier: Modifier = Modifier,
    containerColor: Color = Color.Transparent,
) {
    var isFavorite by
        remember(agentId) { mutableStateOf(IntySetting.isExploreAgentFavorite(agentId)) }
    // 与探索页角色卡片保持一致：未收藏时显示空心图标，收藏后显示粉色实心图标
    val favoriteIcon = if (isFavorite) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder
    val favoriteTint =
        if (isFavorite) UiConfigs.ChatTopBar.FavoriteActiveTint
        else UiConfigs.ChatTopBar.FavoriteInactiveTint
    val favoriteDescription =
        if (isFavorite) stringResource(R.string.favorite_button_remove_from_favorites)
        else stringResource(R.string.favorite_button_add_to_favorites)

    IconButton(
        modifier = modifier.size(UiConfigs.ChatTopBar.FavoriteButtonSize),
        onClick = {
            val nextFavorite = !isFavorite
            isFavorite = nextFavorite
            IntySetting.setExploreAgentFavorite(agentId, nextFavorite)
        },
        colors =
            IconButtonDefaults.iconButtonColors(
                contentColor = favoriteTint,
                containerColor = containerColor,
            ),
    ) {
        Icon(
            imageVector = favoriteIcon,
            contentDescription = favoriteDescription,
            tint = favoriteTint,
            modifier = Modifier.size(UiConfigs.ChatTopBar.FavoriteIconSize),
        )
    }
}

/**
 * VIP 角标组件
 *
 * 使用场景：
 * - 聊天页面顶部栏展示 VIP 角色标识，与 Explore 页面视觉一致。
 *
 * 预期视觉效果：
 * - 在容器左上角绘制高饱和黄色三角角标。
 * - 角标内展示 “VIP” 文案，增强识别。
 *
 * 可配置项：
 * - label: 角标文案（通常来自 string 资源）
 * - contentDescription: 无障碍描述
 * - cornerSize: 角标尺寸
 * - textPaddingTop/textPaddingStart: 文案内边距
 * - textSize: 文案大小
 */
@Composable
private fun VipCornerBadge(
    modifier: Modifier = Modifier,
    label: String,
    contentDescription: String,
    cornerSize: Dp = UiConfigs.ChatTopBar.VipBadge.CornerSize,
    textPaddingTop: Dp = UiConfigs.ChatTopBar.VipBadge.TextPaddingTop,
    textPaddingStart: Dp = UiConfigs.ChatTopBar.VipBadge.TextPaddingStart,
    textSize: TextUnit = UiConfigs.ChatTopBar.VipBadge.TextSize,
) {
    Box(
        modifier =
            modifier.size(cornerSize).semantics {
                this.contentDescription = contentDescription
            }
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val triangle =
                Path().apply {
                    moveTo(0f, 0f)
                    lineTo(size.width, 0f)
                    lineTo(0f, size.height)
                    close()
                }
            drawPath(path = triangle, color = AppColors.VipHighlighterStrong)
        }

        Text(
            text = label,
            modifier =
                Modifier.align(Alignment.TopStart)
                    .padding(top = textPaddingTop, start = textPaddingStart),
            fontSize = textSize,
            fontWeight = FontWeight.Black,
            color = AppColors.Background,
            maxLines = 1,
        )
    }
}

/** 聊天页面顶部栏组件 */
@Composable
fun ChatTopBar(
    navController: NavController,
    modifier: Modifier,
    agentInfo: AgentInfo,
    onClickMore: () -> Unit,
    onClickCall: () -> Unit,
    avatarWidth: Dp = UiConfigs.ChatTopBar.AvatarSize,
    fontSize: TextUnit = 14.sp,
    earnedPoints: Int? = null,
    showBackButton: Boolean = false,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val isVip = remember(agentInfo.tags) { isVipAgent(agentInfo.tags) }

    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        // 返回按钮：showBackButton 为 true 时显示，样式与电话/更多按钮一致（半透明圆角背景），图标使用 R.drawable.back 与其他页面统一
        if (showBackButton) {
            Box(
                modifier = Modifier.noRippleClickable { navController.popBackStack() },
                contentAlignment = Alignment.Center,
            ) {
                Image(
                    painter = painterResource(R.drawable.back),
                    contentDescription = stringResource(R.string.content_desc_back),
                    colorFilter = ColorFilter.tint(Color.White),
                    modifier = Modifier.size(UiConfigs.ChatTopBar.MoreButtonIconSize),
                )
            }
            Spacer(modifier = Modifier.width(UiConfigs.ChatTopBar.BackButtonToAvatarSpacing))
        }
        Box(
            modifier =
                Modifier.background(
                        color = UiConfigs.ChatTopBar.BackgroundColor,
                        shape = RoundedCornerShape(UiConfigs.ChatTopBar.CornerRadius),
                    )
                    .noRippleClickable {
                        scope.launch {
                            // 如果是已经删除的agent，则不可点击，并提示
                            if (agentInfo.isDeleted) {
                                ToastUtils.showShort(R.string.str_agent_is_deleted)
                            } else {
                                AgentStore.addAgent(agentInfo)
                                navController.navigate(Routes.Home.agentInfPage(agentInfo.id))
                            }
                        }
                    },
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                AsyncImage(
                    modifier =
                        Modifier.padding(UiConfigs.ChatTopBar.AvatarPadding)
                            .size(avatarWidth)
                            .clip(CircleShape),
                    model =
                        ImageRequest.Builder(context)
                            .data(getCdnImageUrl(agentInfo.avatar, width = 64))
                            .build(),
                    placeholder = painterResource(R.drawable.img_default_avatar),
                    error = painterResource(R.drawable.img_default_avatar),
                    contentDescription = null,
                    alignment = Alignment.TopCenter,
                    contentScale = ContentScale.Crop,
                )

                Spacer(modifier = Modifier.width(UiConfigs.ChatTopBar.AvatarToContentSpacing))

                val showPoints = earnedPoints != null

                // 名字区域 - 不使用 weight，让所有元素靠左对齐
                Column {
                    // 能量点数区域，目前还未开放显示角色能量点数；需要不断跟踪角色跟用户聊天的共享点数
                    // 而不是角色总共的 credits，因为那样用户感觉没有实际的提升。
                    if (showPoints) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Rounded.EnergySavingsLeaf,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(UiConfigs.ChatTopBar.EnergyIconSize),
                            )
                            Spacer(
                                modifier = Modifier.width(UiConfigs.ChatTopBar.EnergyIconToTextSpacing)
                            )
                            Text(
                                text =
                                    stringResource(
                                        id = R.string.energy_points_counter,
                                        earnedPoints,
                                    ),
                                fontSize = UiConfigs.ChatTopBar.EnergyPointsFontSize,
                                color = Color.White.copy(alpha = 0.9f),
                                fontWeight = FontWeight.Medium,
                            )
                        }
                        Spacer(
                            modifier =
                                Modifier.height(UiConfigs.ChatTopBar.EnergyPointsToNameSpacing)
                        )
                    }
                    Text(
                        text = agentInfo.name,
                        fontSize = fontSize,
                        fontWeight = FontWeight.Medium,
                        color = Color.White,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }

                // 名字与收藏按钮之间的间距 - 紧贴名字右侧
                Spacer(modifier = Modifier.width(0.dp))

                // 收藏按钮 - 移动到横幅内，名字的右侧
                FavoriteButton(agentId = agentInfo.id, containerColor = Color.Transparent)

                // 收藏按钮右侧内边距
                Spacer(modifier = Modifier.width(4.dp))
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        if (isVip) {
            val vipContentDesc = stringResource(R.string.vip_badge_content_description)
            Box(
                modifier =
                    Modifier.size(
                            UiConfigs.ChatTopBar.ActionButtonContainerWidth,
                            UiConfigs.ChatTopBar.ActionButtonContainerHeight,
                        )
                        .background(
                            color = AppColors.VipHighlighterStrong,
                            shape =
                                RoundedCornerShape(
                                    UiConfigs.ChatTopBar.ActionButtonContainerCornerRadius
                                ),
                        )
                        .semantics { contentDescription = vipContentDesc },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = stringResource(R.string.vip_badge_label),
                    fontSize = UiConfigs.ChatTopBar.VipBadge.TextSize,
                    fontWeight = FontWeight.Black,
                    color = AppColors.Background,
                    maxLines = 1,
                )
            }
            Spacer(modifier = Modifier.width(UiConfigs.ChatTopBar.ActionButtonSpacing))
        }

        Box(
            modifier =
                Modifier.size(
                        UiConfigs.ChatTopBar.ActionButtonContainerWidth,
                        UiConfigs.ChatTopBar.ActionButtonContainerHeight,
                    )
                    .background(
                        color =
                            Color.Black.copy(
                                alpha = UiConfigs.ChatTopBar.ActionButtonContainerAlpha
                            ),
                        shape =
                            RoundedCornerShape(
                                UiConfigs.ChatTopBar.ActionButtonContainerCornerRadius
                            ),
                    )
                    .noRippleClickable { onClickCall() },
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Filled.Call,
                contentDescription = stringResource(R.string.call),
                tint = Color.White,
                modifier = Modifier.size(UiConfigs.ChatTopBar.MoreButtonIconSize),
            )
        }

        Spacer(modifier = Modifier.width(UiConfigs.ChatTopBar.ActionButtonSpacing))

        Box(
            modifier =
                Modifier.size(
                        UiConfigs.ChatTopBar.ActionButtonContainerWidth,
                        UiConfigs.ChatTopBar.ActionButtonContainerHeight,
                    )
                    .background(
                        color =
                            Color.Black.copy(
                                alpha = UiConfigs.ChatTopBar.ActionButtonContainerAlpha
                            ),
                        shape =
                            RoundedCornerShape(
                                UiConfigs.ChatTopBar.ActionButtonContainerCornerRadius
                            ),
                    ),
            contentAlignment = Alignment.Center,
        ) {
            AsyncImage(
                modifier =
                    Modifier.size(UiConfigs.ChatTopBar.MoreButtonIconSize).noRippleClickable {
                        onClickMore()
                    },
                model = R.drawable.icon_more,
                contentDescription = null,
            )
        }
    }
}
