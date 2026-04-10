package com.ai.imate.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.outlined.ChatBubbleOutline
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Flag
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.core.ui.theme.ChatSettingsColors
import com.ai.core.utils.getCdnImageUrl
import com.ai.imate.R
import com.ai.imate.chat.data.bean.AgentInfo

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatSettingsBottomSheet(
    agent: AgentInfo,
    visible: Boolean,
    onDismiss: () -> Unit,
    onSendFeedback: () -> Unit,
    onReportIssue: () -> Unit,
    onOpenTerms: () -> Unit,
    onOpenPrivacy: () -> Unit,
    onLogout: () -> Unit,
    onDeleteAccount: () -> Unit,
) {
    if (!visible) return

    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = ChatSettingsColors.SheetBackground,
        dragHandle = {
            Box(
                modifier =
                    Modifier
                        .padding(top = 12.dp)
                        .width(40.dp)
                        .height(4.dp)
                        .clip(CircleShape)
                        .background(ChatSettingsColors.DragHandle),
            )
        },
        tonalElevation = 0.dp,
    ) {
        ChatSettingsSheetContent(
            agent = agent,
            onClose = onDismiss,
            onSendFeedback = onSendFeedback,
            onReportIssue = onReportIssue,
            onOpenTerms = onOpenTerms,
            onOpenPrivacy = onOpenPrivacy,
            onLogout = onLogout,
            onDeleteAccount = onDeleteAccount,
        )
    }
}

@Composable
private fun ChatSettingsSheetContent(
    agent: AgentInfo,
    onClose: () -> Unit,
    onSendFeedback: () -> Unit,
    onReportIssue: () -> Unit,
    onOpenTerms: () -> Unit,
    onOpenPrivacy: () -> Unit,
    onLogout: () -> Unit,
    onDeleteAccount: () -> Unit,
) {
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(bottom = 24.dp),
    ) {
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(57.dp)
                    .padding(horizontal = 20.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                text = stringResource(R.string.chat_settings_title),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                lineHeight = 27.sp,
            )
            IconButton(
                onClick = onClose,
                modifier =
                    Modifier
                        .size(32.dp)
                        .background(ChatSettingsColors.CloseButtonBackground, CircleShape),
            ) {
                Icon(
                    imageVector = Icons.Outlined.Close,
                    contentDescription = stringResource(R.string.content_desc_close_settings),
                    tint = Color.White,
                    modifier = Modifier.size(16.dp),
                )
            }
        }

        HorizontalDivider(
            modifier = Modifier.fillMaxWidth(),
            thickness = 1.dp,
            color = ChatSettingsColors.RowDivider,
        )

        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
        ) {
            ProfileSummaryCard(agent = agent)

            Spacer(modifier = Modifier.height(16.dp))

            SettingsRow(
                icon = Icons.Outlined.ChatBubbleOutline,
                iconBackground = ChatSettingsColors.IconTileBackground,
                title = stringResource(R.string.chat_send_feedback_title),
                subtitle = stringResource(R.string.chat_send_feedback_subtitle),
                titleColor = Color.White,
                onClick = onSendFeedback,
            )
            SettingsRow(
                icon = Icons.Outlined.Flag,
                iconBackground = ChatSettingsColors.IconTileBackground,
                title = stringResource(R.string.chat_report_issue_title),
                subtitle = stringResource(R.string.chat_report_issue_subtitle),
                titleColor = Color.White,
                onClick = onReportIssue,
            )
            SettingsRow(
                icon = Icons.Outlined.Description,
                iconBackground = ChatSettingsColors.IconTileBackground,
                title = stringResource(R.string.chat_terms_title),
                subtitle = stringResource(R.string.chat_terms_subtitle),
                titleColor = Color.White,
                onClick = onOpenTerms,
            )
            SettingsRow(
                icon = Icons.Outlined.Shield,
                iconBackground = ChatSettingsColors.IconTileBackground,
                title = stringResource(R.string.chat_privacy_title),
                subtitle = stringResource(R.string.chat_privacy_subtitle),
                titleColor = Color.White,
                onClick = onOpenPrivacy,
            )

            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider(
                modifier = Modifier.fillMaxWidth(),
                thickness = 1.dp,
                color = ChatSettingsColors.RowDivider,
            )
            Spacer(modifier = Modifier.height(8.dp))

            SettingsRow(
                icon = Icons.AutoMirrored.Outlined.Logout,
                iconBackground = ChatSettingsColors.IconTileBackground,
                title = stringResource(R.string.chat_logout_title),
                subtitle = stringResource(R.string.chat_logout_subtitle),
                titleColor = Color.White,
                onClick = onLogout,
            )
            SettingsRow(
                icon = Icons.Outlined.DeleteOutline,
                iconBackground = ChatSettingsColors.DestructiveIconBackground,
                title = stringResource(R.string.chat_delete_account_title),
                subtitle = stringResource(R.string.chat_delete_account_subtitle),
                titleColor = Color(0xFFE53E3E),
                onClick = onDeleteAccount,
            )
        }
    }
}

@Composable
private fun ProfileSummaryCard(agent: AgentInfo) {
    val shape = RoundedCornerShape(12.dp)
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(shape)
                .border(1.dp, ChatSettingsColors.ProfileCardBorder, shape)
                .background(ChatSettingsColors.ProfileCardBackground)
                .padding(horizontal = 16.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val url = agent.avatar.takeIf { it.isNotBlank() }?.let { getCdnImageUrl(it) }
        Box(
            modifier =
                Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(ChatSettingsColors.IconTileBackground),
            contentAlignment = Alignment.Center,
        ) {
            if (url != null) {
                AsyncImage(
                    model = url,
                    contentDescription = stringResource(R.string.content_desc_agent_avatar),
                    modifier = Modifier.size(44.dp).clip(CircleShape),
                    contentScale = ContentScale.Crop,
                )
            }
        }
        Spacer(modifier = Modifier.width(16.dp))
        Column {
            Text(
                text = agent.name.ifBlank { stringResource(R.string.app_name) },
                color = Color.White,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                lineHeight = 22.5.sp,
            )
            Text(
                text = stringResource(R.string.chat_companion_subtitle),
                color = Color.White.copy(alpha = 0.4f),
                fontSize = 12.sp,
                lineHeight = 18.sp,
            )
        }
    }
}

@Composable
private fun SettingsRow(
    icon: ImageVector,
    iconBackground: Color,
    title: String,
    subtitle: String,
    titleColor: Color,
    onClick: () -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .clickable(onClick = onClick)
                .padding(vertical = 12.dp, horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier =
                Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(iconBackground),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (titleColor == Color(0xFFE53E3E)) titleColor else Color.White.copy(alpha = 0.9f),
                modifier = Modifier.size(18.dp),
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column {
            Text(
                text = title,
                color = titleColor,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                lineHeight = 21.sp,
            )
            Text(
                text = subtitle,
                color = Color.White.copy(alpha = 0.4f),
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                lineHeight = 18.sp,
            )
        }
    }
}
