package com.ai.intellimate.settings

import ai.sxwl.android.design.ui.IntelliMateDivider
import ai.sxwl.android.design.ui.SettingsArrowItem
import ai.sxwl.android.design.ui.SettingsItemData
import ai.sxwl.android.design.ui.SettingsItemGroup
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import com.ai.intellimate.R

/** 账号操作分组，包含退出登录与删除账号 */
@Composable
fun LogoutButton(
    modifier: Modifier = Modifier,
    onLogout: () -> Unit = {},
    onDeleteAccount: () -> Unit = {},
) {
    SettingsItemGroup(modifier = modifier) {
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(title = stringResource(R.string.logout)),
            isInGroup = true,
            onItemClick = onLogout,
        )

        IntelliMateDivider()

        SettingsArrowItem(
            item =
                SettingsItemData.CommonItemData(
                    title = stringResource(R.string.settings_str_delete_account)
                ),
            isInGroup = true,
            onItemClick = onDeleteAccount,
        )
    }
}

@Preview
@Composable
private fun 预览登出按钮() {
    LogoutButton()
}
