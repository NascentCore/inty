package com.ai.intellimate.settings.check

import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostError
import com.ai.intellimate.boost.BoostException
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.ui.BoostStatusChip
import kotlinx.coroutines.launch

@Composable
fun CheckInScreen(navController: NavController) {
    val configuration = LocalConfiguration.current
    val screenHeightDp = configuration.screenHeightDp.dp
    val screenWidthDp = configuration.screenWidthDp.dp
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val boostState by BoostManager.boostState.collectAsState()

    // 1. 获取月份信息
    val (daysInMonth, today) = remember { getCurrentMonthInfo() }
    // 2. SharedPreferences 数据状态：存储当前月所有已签到的日期集合
    var checkedInDays by remember {
        // 首次加载时，从 SharedPreferences 读取数据
        mutableStateOf(CheckInRepository.getCheckedInDays())
    }
    val hasClaimedDailyReward = boostState.hasClaimedDailyReward
    val isCheckedToday = checkedInDays.contains(today)
    val hasCheckedInToday = isCheckedToday || hasClaimedDailyReward
    val btnText =
        if (hasCheckedInToday) stringResource(R.string.boost_daily_reward_claimed)
        else stringResource(R.string.boost_daily_reward_cta)

    LaunchedEffect(hasClaimedDailyReward) {
        if (hasClaimedDailyReward && !isCheckedToday) {
            CheckInRepository.checkInDay(today)
            checkedInDays = CheckInRepository.getCheckedInDays()
        }
    }

    Box(
        modifier =
            Modifier.fillMaxSize().background(ai.sxwl.android.design.theme.HeartColor.primaryColor)
    ) {
        Image(
            painter = painterResource(R.drawable.check_in_bg),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
        )

        Column(modifier = Modifier.fillMaxWidth()) {
            CheckInNavigation(onClose = { navController.popBackStack() })

            // Credits 横幅
            Spacer(modifier = Modifier.height(16.dp))
            Box(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                contentAlignment = Alignment.Center,
            ) {
                BoostStatusChip(
                    navController,
                    modifier = Modifier.fillMaxWidth(),
                    availablePoints = boostState.availablePoints,
                )
            }

            Spacer(modifier = Modifier.height(screenHeightDp * 0.08f))
            Text(
                text = stringResource(R.string.check_in_day_together, checkedInDays.count()),
                modifier = Modifier.align(Alignment.CenterHorizontally),
                letterSpacing = 0.6.sp,
                style =
                    TextStyle(
                        fontSize = 26.sp,
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        shadow =
                            Shadow(
                                // 淡淡的白色阴影
                                color = Color.White.copy(alpha = 0.8f), // 稍微透明的白色
                                // 阴影的偏移量，微小的右下方偏移
                                offset = Offset(6f, 6f),
                                // 模糊半径，让阴影更柔和
                                blurRadius = 8f,
                            ),
                    ),
            )

            Spacer(modifier = Modifier.height(screenHeightDp * 0.03f))
            Text(
                text = "Keep a record of your daily moment with IntelliMate",
                style = TextStyle(fontSize = 13.sp, color = Color.White),
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )

            Spacer(modifier = Modifier.height(screenHeightDp * 0.06f))
            Row(modifier = Modifier.fillMaxWidth().height(86.dp)) {
                DaySelectorRow(daysInMonth, today, checkedInDays)
            }

            // 签到按钮
            Spacer(modifier = Modifier.height(screenHeightDp * 0.03f))
            Box(
                modifier =
                    Modifier.width(screenWidthDp * 0.91f)
                        .height(56.dp)
                        .background(
                            brush =
                                Brush.linearGradient(
                                    colors =
                                        if (hasCheckedInToday)
                                            listOf(Color(0x509756FF), Color(0x50EF56FF))
                                        else listOf(Color(0xFF9756FF), Color(0xFFEF56FF))
                                ),
                            shape = RoundedCornerShape(28.dp),
                        )
                        .clickable {
                            if (hasCheckedInToday) {
                                ToastUtils.showShort(R.string.boost_daily_reward_already)
                                return@clickable
                            }

                            scope.launch {
                                try {
                                    val claimed = BoostManager.claimDailyReward()
                                    ToastUtils.showLong(
                                        context.getString(
                                            R.string.boost_toast_daily_reward_claimed,
                                            claimed,
                                        )
                                    )
                                    CheckInRepository.checkInDay(today)
                                    checkedInDays = CheckInRepository.getCheckedInDays()
                                } catch (e: BoostException) {
                                    val messageRes =
                                        when (e.error) {
                                            BoostError.DailyRewardAlreadyClaimed ->
                                                R.string.boost_daily_reward_already
                                            BoostError.NotEnoughPoints ->
                                                R.string.boost_toast_not_enough_points
                                            else -> R.string.boost_toast_generic_error
                                        }
                                    ToastUtils.showShort(messageRes)
                                    if (
                                        e.error == BoostError.DailyRewardAlreadyClaimed &&
                                            !checkedInDays.contains(today)
                                    ) {
                                        CheckInRepository.checkInDay(today)
                                        checkedInDays = CheckInRepository.getCheckedInDays()
                                    }
                                } catch (_: Exception) {
                                    ToastUtils.showShort(R.string.boost_toast_generic_error)
                                }
                            }
                        }
                        .align(Alignment.CenterHorizontally),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = btnText,
                    style =
                        TextStyle(
                            fontSize = 17.sp,
                            color = Color.White.copy(alpha = if (hasCheckedInToday) 0.5f else 1f),
                            fontWeight = FontWeight.Bold,
                        ),
                )
            }

            // 底部文字
            Spacer(modifier = Modifier.height(screenHeightDp * 0.02f))
            Text(
                text = "More benefits coming soon",
                style = TextStyle(fontSize = 12.sp, color = Color.White.copy(0.6f)),
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CheckInNavigation(onClose: () -> Unit) {
    CenterAlignedTopAppBar(
        title = {
            Text(text = "Today's Check-in", fontWeight = FontWeight(600), color = Color.White)
        },
        modifier = Modifier.fillMaxWidth(),
        navigationIcon = {
            IconButton(onClick = onClose) {
                Image(
                    painter = painterResource(R.drawable.back),
                    contentDescription = stringResource(R.string.content_desc_back),
                )
            }
        },
        colors = TopAppBarDefaults.topAppBarColors().copy(containerColor = Color.Transparent),
    )
}

@Composable
fun DaySelectorRow(daysInMonth: Int, today: Int, checkedInDays: Set<Int>) {
    // 2. 创建一个包含当月所有天数的列表（1, 2, 3, ..., daysInMonth）
    val daysList = remember { (1..daysInMonth).toList() }

    // 3. LazyRow 的状态，用于控制滚动
    val lazyListState = rememberLazyListState()

    // 4. CoroutineScope 用于在 Compose 中启动协程（例如：滚动）
    val coroutineScope = rememberCoroutineScope()

    // 5. 初始滚动到今天
    // LaunchedEffect 会在 Composable 首次进入组合时执行一次，
    // 用于执行 side effect，这里是滚动操作。
    LaunchedEffect(key1 = Unit) {
        // 滚动到 'today' 的索引。因为 daysList 是 1-based，索引是 (today - 1)
        val initialScrollIndex = today - 1
        // 使用 animateScrollToItem 实现平滑滚动
        coroutineScope.launch {
            lazyListState.animateScrollToItem(
                index = initialScrollIndex,
                // 偏移量用于确保目标项居中或至少可见。
                // 100.dp 是 Box 的宽度。
                // 如果你想让今天的 Box 尽可能居中，可能需要更复杂的计算。
                // 这里我们只是确保它在屏幕上可见。
                scrollOffset = -300, // 负值是为了让它从左侧滚动进来
            )
        }
    }

    // 6. 渲染 LazyRow
    LazyRow(
        state = lazyListState,
        // 添加内边距，让第一个和最后一个元素不会紧贴边缘
        contentPadding = PaddingValues(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp), // 间距
        modifier = Modifier.fillMaxWidth().height(116.dp), // 100dp Box + 顶部底部内边距
    ) {
        items(daysList) { day ->
            // 7. 渲染每一天的 Box
            val index = checkedInDays.indexOf(day)
            DayItem(day = day, today = today, index)
        }
    }
}

/** 单个日期的 Composable */
@Composable
fun DayItem(day: Int, today: Int, index: Int) {
    val isCheck = index >= 0
    val strMonth = getCurrentMonthAbbreviation()
    val isToday = day == today
    val isMissed = day < today && !isCheck
    if (isToday) {
        DayItemToday(isCheck = isCheck, day)
    } else if (isCheck) { // 已签到
        DayItemChecked(day, strMonth, index)
    } else {
        if (isMissed) { // 历史未签到
            DayItemUncheck(day, strMonth)
        } else { // 未来未签到
            DayItemWaitToCheck(day, strMonth)
        }
    }
}

@Composable
fun DayItemToday(isCheck: Boolean, day: Int) {
    Box(
        modifier =
            Modifier.width(76.dp)
                .height(88.dp)
                .background(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color(0xFFC2F7FD), Color(0xFFC4A9FC), Color(0xFF7E96FB)),
                            start = Offset(0f, 0f),
                            end = Offset(Float.POSITIVE_INFINITY, 0f),
                        ),
                    shape = RoundedCornerShape(8.dp),
                )
    ) {
        Box(
            modifier =
                Modifier.width(72.dp)
                    .height(81.dp)
                    .background(
                        brush =
                            Brush.linearGradient(
                                colors = listOf(Color(0xFF9756FF), Color(0xFF350D5D)),
                                start = Offset(0f, 0f),
                                end = Offset(0f, Float.POSITIVE_INFINITY),
                            ),
                        shape = RoundedCornerShape(6.dp),
                    )
                    .align(Alignment.Center)
        ) {
            Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Spacer(modifier = Modifier.weight(1f))
                Text(
                    text = "NOW",
                    style =
                        TextStyle(
                            fontSize = 12.sp,
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                        ),
                )
                Spacer(modifier = Modifier.height(12.dp))
                Image(
                    painter =
                        painterResource(
                            if (isCheck) R.drawable.check_in_ok else R.drawable.check_in_calendar
                        ),
                    contentDescription = null,
                    modifier = Modifier.width(20.dp).height(20.dp),
                    contentScale = ContentScale.Fit,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(text = "Today", style = TextStyle(fontSize = 12.sp, color = Color.White))
                Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
fun DayItemUncheck(day: Int, strMonth: String) {
    Box(
        modifier =
            Modifier.width(76.dp)
                .height(88.dp)
                .background(
                    Color(red = 98, green = 96, blue = 101),
                    shape = RoundedCornerShape(8.dp),
                )
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(
                modifier =
                    Modifier.width(76.dp)
                        .height(28.dp)
                        .background(
                            Color(93, 91, 96),
                            shape = RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp),
                        )
            ) {
                Text(
                    text = "Unchecked",
                    modifier = Modifier.align(Alignment.Center),
                    style =
                        TextStyle(
                            fontSize = 12.sp,
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                        ),
                )
            }

            Spacer(modifier = Modifier.height(5.dp))
            Image(
                painter = painterResource(R.drawable.ic_checkin),
                contentDescription = null,
                modifier = Modifier.width(20.dp).height(20.dp),
                contentScale = ContentScale.Fit,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "$strMonth $day", style = TextStyle(fontSize = 12.sp, color = Color.White))
            Spacer(modifier = Modifier.weight(1f))
        }

        Box(
            modifier =
                Modifier.fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.4f), shape = RoundedCornerShape(8.dp))
        )
    }
}

@Composable
fun DayItemChecked(day: Int, strMonth: String, index: Int) {
    Box(
        modifier =
            Modifier.width(76.dp)
                .height(88.dp)
                .background(
                    brush =
                        Brush.linearGradient(
                            colors = listOf(Color(0xFF9756FF), Color(0xFF350D5D)),
                            start = Offset(0f, 0f),
                            end = Offset(0f, Float.POSITIVE_INFINITY),
                        ),
                    shape = RoundedCornerShape(8.dp),
                )
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(modifier = Modifier.weight(1f))
            Text(
                text = "Day ${index + 1}",
                style =
                    TextStyle(fontSize = 12.sp, color = Color.White, fontWeight = FontWeight.Bold),
            )
            Spacer(modifier = Modifier.height(5.dp))
            Image(
                painter = painterResource(R.drawable.check_in_ok),
                contentDescription = null,
                modifier = Modifier.width(20.dp).height(20.dp),
                contentScale = ContentScale.Fit,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "$strMonth $day", style = TextStyle(fontSize = 12.sp, color = Color.White))
            Spacer(modifier = Modifier.weight(1f))
        }

        Box(
            modifier =
                Modifier.fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.6f), shape = RoundedCornerShape(8.dp))
        )
    }
}

@Composable
fun DayItemWaitToCheck(day: Int, strMonth: String) {
    Box(
        modifier =
            Modifier.width(76.dp)
                .height(88.dp)
                .background(
                    Color(red = 83, green = 64, blue = 108),
                    shape = RoundedCornerShape(8.dp),
                )
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(
                modifier =
                    Modifier.width(76.dp)
                        .height(28.dp)
                        .background(
                            Color(69, 44, 88),
                            shape = RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp),
                        )
            ) {
                Text(
                    text = "Upcoming",
                    modifier = Modifier.align(Alignment.Center),
                    style =
                        TextStyle(
                            fontSize = 12.sp,
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                        ),
                )
            }

            Spacer(modifier = Modifier.height(5.dp))
            Image(
                painter = painterResource(R.drawable.check_in_calendar),
                contentDescription = null,
                modifier = Modifier.width(20.dp).height(20.dp),
                contentScale = ContentScale.Fit,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "$strMonth $day", style = TextStyle(fontSize = 12.sp, color = Color.White))
            Spacer(modifier = Modifier.weight(1f))
        }
    }
}
