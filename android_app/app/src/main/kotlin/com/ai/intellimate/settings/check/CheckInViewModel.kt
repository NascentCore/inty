import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.YearMonth

// 1. 定义日期状态类型
sealed class AttendanceStatus {
    data object Signed : AttendanceStatus()     // 已签到 (红色)
    data object Missed : AttendanceStatus()     // 历史未签到 (蓝色)
    data object Future : AttendanceStatus()     // 当日/未来未签到 (紫色)
}

// 2. 定义页面整体状态
data class AttendanceUiState(
    // 存储当前月份的所有日期及其签到状态
    val datesInMonth: Map<LocalDate, AttendanceStatus> = emptyMap(),
    // 存储用户已签到的具体日期（方便签到逻辑）
    val signedInDates: Set<LocalDate> = emptySet(),
    val currentMonth: YearMonth = YearMonth.now(),
    val isTodaySignedIn: Boolean = false
)

class AttendanceViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(AttendanceUiState())
    val uiState: StateFlow<AttendanceUiState> = _uiState.asStateFlow()

    // 假设这是从数据库加载的历史签到数据
    // 初始设置：假设用户在 2025-11-01 和 2025-11-20 签到过 (当前是 2025-11-29)
    private val initialSigned = setOf(
        LocalDate.of(2025, 11, 1),
        LocalDate.of(2025, 11, 20)
    )

    init {
        // 首次加载当前月份的日历
        loadMonth(YearMonth.now())
    }

    // 核心逻辑：加载指定月份的日历状态
    fun loadMonth(month: YearMonth) {
        viewModelScope.launch {
            val today = LocalDate.now()
            val firstDayOfMonth = month.atDay(1)
            val lastDayOfMonth = month.atEndOfMonth()

            val datesMap = mutableMapOf<LocalDate, AttendanceStatus>()
            val signedDates = if (month == YearMonth.now()) initialSigned else emptySet()

            var date = firstDayOfMonth
            while (date.isBefore(lastDayOfMonth) || date.isEqual(lastDayOfMonth)) {

                val status = when {
                    // 规则 1: 当月已签到的显示为红色 (Signed)
                    signedDates.contains(date) -> AttendanceStatus.Signed

                    // 规则 2: 历史未签到的为蓝色 (Missed)
                    date.isBefore(today) -> AttendanceStatus.Missed

                    // 规则 3: 当日以及未来未签到日期为紫色 (Future)
                    else -> AttendanceStatus.Future
                }
                datesMap[date] = status
                date = date.plusDays(1)
            }

            _uiState.update {
                it.copy(
                    datesInMonth = datesMap,
                    signedInDates = signedDates,
                    currentMonth = month,
                    isTodaySignedIn = signedDates.contains(today) // 更新当日签到状态
                )
            }
        }
    }

    // 核心功能：当日签到方法
    fun signInToday() {
        val today = LocalDate.now()
        // 避免重复签到
        if (_uiState.value.isTodaySignedIn) return

        viewModelScope.launch {
            // 模拟将签到记录保存到服务器/本地，并更新本地状态

            val updatedSignedDates = _uiState.value.signedInDates + today
            val updatedDatesMap = _uiState.value.datesInMonth.toMutableMap()

            // 只有当月的日期才需要立即在 datesInMonth 中更新
            if (today.year == _uiState.value.currentMonth.year && today.month == _uiState.value.currentMonth.month) {
                updatedDatesMap[today] = AttendanceStatus.Signed
            }

            _uiState.update {
                it.copy(
                    signedInDates = updatedSignedDates,
                    datesInMonth = updatedDatesMap,
                    isTodaySignedIn = true
                )
            }
        }
    }
}