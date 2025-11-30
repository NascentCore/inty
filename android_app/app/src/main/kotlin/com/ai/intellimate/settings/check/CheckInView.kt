package com.ai.intellimate.settings.check

import AttendanceStatus
import AttendanceViewModel
import android.content.Context
import android.util.Log
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.ai.intellimate.R

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling
import kotlinx.coroutines.launch
import java.time.LocalDate

@Composable
fun CheckInScreen(
    context: Context,
    onClose: () -> Unit,
    viewModel: AttendanceViewModel = viewModel()
) {
    val configuration = LocalConfiguration.current
    val screenHeightDp = configuration.screenHeightDp.dp
    val screenWidthDp = configuration.screenWidthDp.dp

    val uiState by viewModel.uiState.collectAsState()
    val today = LocalDate.now()
    val isCheckedToday = uiState.isTodaySignedIn;
    Log.d("SLLog", "----------->${uiState.isTodaySignedIn}")

    Box(modifier = Modifier.fillMaxSize().background(ai.sxwl.android.design.theme.HeartColor.primaryColor)) {
        Image(
            painter = painterResource(R.drawable.check_in_bg),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop
        )

        Column(modifier = Modifier.fillMaxWidth()) {
            CheckInNavigation(
                onClose = onClose
            )

            Spacer(modifier = Modifier.height(screenHeightDp * 0.08f))
            Image(
                painter = painterResource(R.drawable.check_in_title),
                contentDescription = null,
                modifier = Modifier.width(343.dp).height(46.dp).align(Alignment.CenterHorizontally),
                contentScale = ContentScale.FillHeight
            )

            Spacer(modifier = Modifier.height(screenHeightDp * 0.03f))
            IgnoreSystemFontScaling {
                Text(
                    text = "Keep a record of your daily moment with IntelliMate",
                    style = TextStyle(fontSize = 13.sp, color = Color.White),
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                )
            }

            Spacer(modifier = Modifier.height(screenHeightDp * 0.06f))
            Row(modifier = Modifier.fillMaxWidth().height(86.dp)) {
                DaySelectorRow(context = context, onTodayIsChecked = {
//                    Log.d("SLTag", "on is Checked today si --------->");
//                    isCheckedToday = true
                })
            }

            // 签到按钮
            Spacer(modifier = Modifier.height(screenHeightDp * 0.03f))
            Box(modifier = Modifier
                .width(screenWidthDp * 0.91f)
                .height(56.dp)
                .background(
                    brush = Brush.linearGradient(
                        colors = if (isCheckedToday) listOf(Color(0x509756FF), Color(0x50EF56FF)) else listOf(Color(0xFF9756FF), Color(0xFFEF56FF))
                    ),
                    shape = RoundedCornerShape(28.dp)
                )
                .clickable {
                    viewModel.signInToday()
                    // 写入 SharedPreferences
                    CheckInRepository.checkInDay(today.dayOfMonth)
                    CheckInRepository.getCheckedInDays()
                }
                .align(Alignment.CenterHorizontally),
                contentAlignment = Alignment.Center,
            ) {
                Text(text = "Check in", style = TextStyle(fontSize = 17.sp, color = Color.White.copy(alpha = if (isCheckedToday) 0.5f else 1f), fontWeight = FontWeight.Bold))
            }

            // 底部文字
            Spacer(modifier = Modifier.height(screenHeightDp * 0.02f))
            IgnoreSystemFontScaling {
                Text(
                    text = "More benefits coming soon",
                    style = TextStyle(fontSize = 12.sp, color = Color.White.copy(0.6f)),
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                )
            }
        }


    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CheckInNavigation(onClose: () -> Unit) {
    CenterAlignedTopAppBar(
        title = { Text(text = "Today's Check-in", fontWeight = FontWeight(600), color = Color.White) },
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
fun DaySelectorRow(context: Context, onTodayIsChecked: () -> Unit) {
    // 本地数据加载
     LaunchedEffect(Unit) { CheckInRepository.initialize(context) }

    // 1. 获取月份信息
    val (daysInMonth, today) = remember { getCurrentMonthInfo() }
    // 1. SharedPreferences 数据状态：存储当前月所有已签到的日期集合
    var checkedInDays by remember {
        // 首次加载时，从 SharedPreferences 读取数据
        mutableStateOf(CheckInRepository.getCheckedInDays())
    }
    Log.d("SLTag", "checked in days i -- -------->$checkedInDays")

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
                scrollOffset = -300 // 负值是为了让它从左侧滚动进来
            )
        }
    }

    // 6. 渲染 LazyRow
    LazyRow(
        state = lazyListState,
        // 添加内边距，让第一个和最后一个元素不会紧贴边缘
        contentPadding = PaddingValues(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp), // 间距
        modifier = Modifier
            .fillMaxWidth()
            .height(116.dp) // 100dp Box + 顶部底部内边距
    ) {
        items(daysList) { day ->
            // 7. 渲染每一天的 Box
            if (checkedInDays.contains(day)) {
                onTodayIsChecked()
            }
            DayItem(day = day, isToday = (day == today), isCheck = checkedInDays.contains(day))
        }
    }
}

/**
 * 单个日期的 Composable
 */
@Composable
fun DayItem(day: Int, isToday: Boolean, isCheck: Boolean) {
    val backgroundColor = if (isToday) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
    val textColor = if (isToday) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
    if (isToday) {
        DayItemToday(
            isCheck = isCheck,
            day
        )
    } else {
        DayItemUncheck(day)
    }
}

@Composable
fun DayItemToday(isCheck: Boolean, day: Int) {
    Box(modifier = Modifier
        .width(76.dp)
        .height(88.dp)
        .background(
            brush = Brush.linearGradient(
                colors = listOf(Color(0xFFC2F7FD), Color(0xFFC4A9FC), Color(0xFF7E96FB)),
                start = Offset(0f, 0f),
                end = Offset(Float.POSITIVE_INFINITY, 0f)
            ),
            shape = RoundedCornerShape(8.dp)
        )
    ) {
        Box(modifier = Modifier
                .width(72.dp)
                .height(81.dp)
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(Color(0xFF9756FF), Color(0xFF350D5D)),
                        start = Offset(0f, 0f),
                        end = Offset(0f, Float.POSITIVE_INFINITY)
                    ),
                    shape = RoundedCornerShape(6.dp)
                )
            .align(Alignment.Center)
        ) {
            Column(modifier = Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
                Spacer(modifier = Modifier.weight(1f))
                Text(text = "Day $day", style = TextStyle(fontSize = 12.sp, color = Color.White, fontWeight = FontWeight.Bold))
                Spacer(modifier = Modifier.height(12.dp))
                Image(
                    painter = painterResource( if (isCheck) R.drawable.check_in_ok else R.drawable.check_in_calendar),
                    contentDescription = null,
                    modifier = Modifier.width(20.dp).height(20.dp),
                    contentScale = ContentScale.Fit
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(text = "Today", style = TextStyle(fontSize = 12.sp, color = Color.White))
                Spacer(modifier = Modifier.weight(1f))
            }

        }
    }
}

@Composable
fun DayItemUncheck(day: Int) {
    Box(modifier = Modifier
        .width(76.dp)
        .height(88.dp)
        .background(
            Color(red = 98, green = 96, blue = 101),
            shape = RoundedCornerShape(8.dp)
        )
    ) {
        Column(modifier = Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
            Spacer(modifier = Modifier.weight(1f))
            Text(text = "Unchecked", style = TextStyle(fontSize = 12.sp, color = Color.White.copy(alpha = 0.8f)))
            Spacer(modifier = Modifier.height(12.dp))
            Image(
                painter = painterResource( R.drawable.ic_checkin),
                contentDescription = null,
                modifier = Modifier.width(20.dp).height(20.dp),
                contentScale = ContentScale.Fit
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "Nov $day", style = TextStyle(fontSize = 12.sp, color = Color.White))
            Spacer(modifier = Modifier.weight(1f))
        }

    }
}

// 渲染日历网格
@Composable
fun DateGrid(datesInMonth: Map<LocalDate, AttendanceStatus>, today: LocalDate) {
    val daysOfWeek = listOf("日", "一", "二", "三", "四", "五", "六")

    // 星期标题
    Row(modifier = Modifier.fillMaxWidth()) {
        daysOfWeek.forEach { day ->
            Text(
                text = day,
                modifier = Modifier.weight(1f),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                fontWeight = FontWeight.Bold
            )
        }
    }

    // 日期列表
    val sortedDates = datesInMonth.keys.sorted()
    if (sortedDates.isEmpty()) return

    // 找出月份第一天是星期几，用于确定网格的偏移量
    val firstDayOfMonth = sortedDates.first()
    val offset = firstDayOfMonth.dayOfWeek.value % 7 // 周日为 0，周一为 1...

    // 创建一个包含所有单元格的扁平列表
    val calendarCells = buildList<LocalDate?> {
        // 填充月份开始前的空白单元格
        repeat(offset) { add(null) }
        // 添加当月日期
        addAll(sortedDates)
    }

    // 将扁平列表转换为 7 列的网格
    LazyColumn(
        contentPadding = PaddingValues(horizontal = 8.dp)
    ) {
        items(calendarCells.chunked(7)) { week ->
            Row(modifier = Modifier.fillMaxWidth()) {
                week.forEach { date ->
                    val status = date?.let { datesInMonth[it] }
                    DateCell(date = date, status = status, isToday = date == today)
                }
            }
        }
    }
}


// 单个日期单元格
@Composable
fun RowScope.DateCell(date: LocalDate?, status: AttendanceStatus?, isToday: Boolean) {

    val backgroundColor = when (status) {
        is AttendanceStatus.Signed -> Color.Red         // 当月已签到
        is AttendanceStatus.Missed -> Color.Blue        // 历史未签到
        is AttendanceStatus.Future -> Color.Yellow      // 当日/未来未签到
        else -> Color.Transparent
    }

    // 设置边框颜色，当日日期更明显
    val borderColor = if (isToday) Color.Black else Color.LightGray

    Box(
        modifier = Modifier
            .weight(1f) // 确保单元格均匀分配宽度
            .aspectRatio(1f) // 使单元格为正方形
            .padding(4.dp)
            .background(
                color = if (date != null) backgroundColor.copy(alpha = 0.8f) else Color.Transparent,
                shape = RoundedCornerShape(8.dp)
            )
            .border(
                width = if (isToday) 2.dp else 1.dp,
                color = borderColor,
                shape = RoundedCornerShape(8.dp)
            )
            .clickable(enabled = false) {}, // 防止误点
        contentAlignment = Alignment.Center
    ) {
        if (date != null) {
            Text(
                text = date.dayOfMonth.toString(),
                color = Color.White,
                fontWeight = if (isToday) FontWeight.ExtraBold else FontWeight.Normal,
                fontSize = 14.sp
            )
        }
    }
}