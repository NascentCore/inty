package ai.sxwl.android.design.ui

import ai.sxwl.android.design.R
import androidx.annotation.DrawableRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * 应用项目封装的items
 */
@Composable
fun SettingsCheckBoxItem(
    item: SettingsItemData.SwitchItemData,
    fontLight: Boolean = false,//使用字重小一点
    isInGroup: Boolean = false,
    lightColor: Boolean = false,//浅色字
    onCheckChanged: (Boolean) -> Unit = {},
) {
    val modifier = if (isInGroup) Modifier else Modifier
        .clip(RoundedCornerShape(8.dp))
        .background(Color(0x3378599A))
        .border(
            width = .05.dp, brush = Brush.horizontalGradient(
                colors = listOf(
                    Color.Transparent,
                    Color.White.copy(.3f),
                    Color.Transparent,
                )
            ),
            shape = RoundedCornerShape(8.dp)
        )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .then(modifier)
            .clickable { onCheckChanged(item.checked.not()) } // 让整个item可点击
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    )
    {
        Text(
            text = item.title,
            fontSize = 14.sp,
            lineHeight = 22.sp,
            fontWeight = if (fontLight) FontWeight.Normal else FontWeight.Bold,
            color = if (lightColor) Color(0X8CFFFFFF) else Color.White,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.weight(1f))
        val iconRes = if (item.checked) R.drawable.ic_checked else R.drawable.ic_unchecked
        Image(
            painter = painterResource(iconRes),
            contentDescription = "",
            modifier = Modifier
                .size(20.dp)
                .clip(CircleShape)
            // 移除checkbox的单独点击，因为整个item已经可点击了
        )
    }
}

/**
 * 只有标题和开关的item
 */
@Composable
fun SettingsSwitchItem(
    item: SettingsItemData.SwitchItemData,
    fontLight: Boolean = false,//使用字重小一点
    isInGroup: Boolean = false,
    onCheckChanged: (Boolean) -> Unit = {},
) {
    val modifier = if (isInGroup) Modifier else Modifier
        .clip(RoundedCornerShape(8.dp))
        .background(Color(0x3378599A))
        .border(
            width = .05.dp, brush = Brush.horizontalGradient(
                colors = listOf(
                    Color.Transparent,
                    Color.White.copy(.3f),
                    Color.Transparent,
                )
            ),
            shape = RoundedCornerShape(8.dp)
        )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .then(modifier)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    )
    {
        Text(
            text = item.title,
            fontSize = 14.sp,
            lineHeight = 22.sp,
            fontWeight = if (fontLight) FontWeight.Normal else FontWeight.Bold,
            color = Color.White,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.weight(1f))
        Switch(
            checked = item.checked,
            onCheckedChange = onCheckChanged,
            colors = SwitchDefaults.colors()
                .copy(
                    checkedTrackColor = Color(0xFF62C18E),
                    uncheckedTrackColor = Color(0xFF43394F),
                    uncheckedBorderColor = Color.Transparent,
                    disabledCheckedBorderColor = Color.Transparent,
                    disabledUncheckedBorderColor = Color.Transparent,
                )
        )
    }
}


/**
 * 设置item的数据类
 */
sealed class SettingsItemData {

    /**
     * 开关设置
     */
    data class SwitchItemData(
        val title: String = "",
        val checked: Boolean = false,
    ) : SettingsItemData()

    /**
     * 普通item数据
     */
    data class CommonItemData(
        val title: String = "",
        val content: String = "",
        val arrow: Boolean = true,
    ) : SettingsItemData()

    /**
     * icon item数据
     */
    data class IconItemData(
        @param:DrawableRes val icon: Int,
        val title: String = "",
        val subTitle: String = "",
    ) : SettingsItemData()


}

@Preview
@Composable
private fun 预览设置开关() {
    Column {
        SettingsSwitchItem(item = SettingsItemData.SwitchItemData("开通VIP", true))
        Spacer(Modifier.height(10.dp))
        SettingsSwitchItem(item = SettingsItemData.SwitchItemData("一键起飞", false))
        Spacer(Modifier.height(10.dp))
        SettingsSwitchItem(item = SettingsItemData.SwitchItemData("轻灵字体", false), true)
        Spacer(Modifier.height(10.dp))
        SettingsCheckBoxItem(item = SettingsItemData.SwitchItemData("一键起飞", true))
        Spacer(Modifier.height(10.dp))
        SettingsCheckBoxItem(item = SettingsItemData.SwitchItemData("轻灵字体", false), true)
    }
}


/**
 * 有标题和描述以及箭头的item
 */
@Composable
fun SettingsArrowItem(
    item: SettingsItemData.CommonItemData,
    fontLight: Boolean = false,//使用字重小一点
    isInGroup: Boolean = false,
    onItemClick: () -> Unit = {},
) {

    val modifier = if (isInGroup) Modifier else Modifier
        .clip(RoundedCornerShape(8.dp))
        .background(Color(0x3378599A))
        .border(
            width = .05.dp, brush = Brush.horizontalGradient(
                colors = listOf(
                    Color.Transparent,
                    Color.White.copy(.3f),
                    Color.Transparent,
                )
            ),
            shape = RoundedCornerShape(8.dp)
        )
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .then(modifier)
            .clickable(onClick = onItemClick)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    )
    {
        Text(
            text = item.title,
            fontSize = 14.sp,
            lineHeight = 22.sp,
            fontWeight = if (fontLight) FontWeight.Normal else FontWeight.Bold,
            color = Color.White,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.width(8.dp))
        Spacer(Modifier.weight(1f))
        Text(
            text = item.content,
            fontSize = 14.sp,
            lineHeight = 22.sp,
            fontWeight = FontWeight(400),
            color = Color(0x8CFFFFFF),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Right,
        )
        if (item.arrow) {
            Spacer(Modifier.width(8.dp))
            Image(
                painter = painterResource(R.drawable.ic_arrow_forward),
                contentDescription = ""
            )
        }
    }
}


@Preview
@Composable
private fun 预览普通设置条目() {
    Column {
        SettingsArrowItem(item = SettingsItemData.CommonItemData("隐私政策"))
        Spacer(Modifier.height(10.dp))
        SettingsArrowItem(item = SettingsItemData.CommonItemData("用户协议", "欢迎查看"))
        Spacer(Modifier.height(10.dp))
        SettingsArrowItem(item = SettingsItemData.CommonItemData("Light用户协议", "欢迎查看"), true)
        Spacer(Modifier.height(10.dp))
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(
                "关于App",
                "v1.0.0",
                arrow = false
            )
        )
    }
}


/**
 * 有图标、标题以及箭头的item
 */
@Composable
fun SettingsIconArrowItem(
    item: SettingsItemData.IconItemData,
    onItemClick: () -> Unit = {},
) {

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(Color(0x3378599A))
            .border(
                width = .05.dp, brush = Brush.horizontalGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.White.copy(.3f),
                        Color.Transparent,
                    )
                ),
                shape = RoundedCornerShape(8.dp)
            )
            .clickable(onClick = onItemClick)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    )
    {
        Image(
            painter = painterResource(item.icon),
            contentDescription = "",
            modifier = Modifier.size(30.dp)
        )

        Spacer(Modifier.width(8.dp))

        Text(
            text = item.title,
            fontSize = 16.sp,
            lineHeight = 22.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.weight(1f))
        Text(
            text = item.subTitle,
            fontSize = 14.sp,
            lineHeight = 22.sp,
            fontWeight = FontWeight(400),
            color = Color(0x8CFFFFFF),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Right,
        )
        Spacer(Modifier.width(8.dp))
        Image(painter = painterResource(R.drawable.ic_arrow_forward), contentDescription = "")

    }
}


@Preview
@Composable
private fun 预览ICON设置条目() {
    SettingsIconArrowItem(
        item = SettingsItemData.IconItemData(
            R.drawable.img_girl_lite,
            "会员订阅",
            "热烈欢迎订阅"
        )
    )
}

/**
 * 设置分组的背景容器
 */
@Composable
fun SettingsItemGroup(
    modifier: Modifier = Modifier,
    horizontal: Alignment.Horizontal = Alignment.CenterHorizontally,
    contents: @Composable ColumnScope.() -> Unit,
) {
    Column(
        Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(Color(0x3378599A))
            .border(
                width = .05.dp, brush = Brush.horizontalGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.White.copy(.3f),
                        Color.Transparent,
                    )
                ),
                shape = RoundedCornerShape(8.dp)
            )
            .then(modifier),
        horizontalAlignment = horizontal,
        verticalArrangement = Arrangement.Center
    ) {
        contents()
    }
}

@Preview
@Composable
private fun 预览设置分组容器() {
    SettingsItemGroup {
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData("隐私政策"),
            isInGroup = true
        )
        IntelliMateDivider()
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData("用户协议", "欢迎查看"),
            isInGroup = true
        )
        IntelliMateDivider()
        SettingsArrowItem(
            item = SettingsItemData.CommonItemData(
                "关于App",
                "v1.0.0",
                arrow = false
            ),
            isInGroup = true
        )
        IntelliMateDivider()
        SettingsCheckBoxItem(
            item = SettingsItemData.SwitchItemData("轻灵字体", true),
            fontLight = true,
            isInGroup = true
        )

    }
}

@Preview
@Composable
fun IntelliMateDivider() {
    Box(
        Modifier
            .fillMaxWidth()
            .height(.2.dp)
            .background(
                brush = Brush.horizontalGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.White.copy(.3f),
                        Color.Transparent,
                    )
                )
            )
    )
}
