import android.content.Context
import android.content.SharedPreferences
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

// 1. 定义存储文件的名称
private const val PREFS_NAME = "checkin_data_prefs"

/**
 * SharedPreferences 签到数据管理单例
 */
object CheckInRepository {

    // 2. 延迟初始化 SharedPreferences 实例，需要 Context
    private lateinit var sharedPreferences: SharedPreferences

    // 3. 日期格式化工具
    private val dateFormatter = SimpleDateFormat("yyyy_MM", Locale.getDefault())

    /**
     * 必须在 Application 或 Activity 中调用此方法进行初始化。
     */
    fun initialize(context: Context) {
        if (!this::sharedPreferences.isInitialized) {
            sharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        }
    }

    /**
     * 根据当前月份生成一个唯一的 SharedPreferences Key。
     * 格式: CHECKIN_YYYY_MM
     */
    private fun getCurrentMonthKey(): String {
        val calendar = Calendar.getInstance()
        val yearMonth = dateFormatter.format(calendar.time)
        return "CHECKIN_$yearMonth"
    }

    /**
     * 获取当前月份所有已签到的日期（Set<Int>）。
     */
    fun getCheckedInDays(): Set<Int> {
        // 确保已初始化
        if (!this::sharedPreferences.isInitialized) {
            // 如果未初始化，返回空集合或抛出错误。
            // 在实际应用中，你需要确保在调用此方法前已调用 initialize()。
            return emptySet()
        }

        val key = getCurrentMonthKey()
        // SharedPreferences 存储 Set<String>
        val stringSet = sharedPreferences.getStringSet(key, emptySet()) ?: emptySet()

        // 转换成 Set<Int> 返回给 Compose
        return stringSet
            .mapNotNull { it.toIntOrNull() }
            .toSet()
    }

    /**
     * 签到指定日期。
     * @param day 要签到的日期数字 (1 - 31)
     */
    fun checkInDay(day: Int) {
        if (!this::sharedPreferences.isInitialized) return // 未初始化则不执行

        val key = getCurrentMonthKey()

        // 1. 读取当前已签到的 Set (Set<Int>)
        val currentIntSet = getCheckedInDays().toMutableSet()

        // 2. 添加新的日期
        currentIntSet.add(day)

        // 3. 转换回 Set<String>
        val stringSetToSave = currentIntSet.map { it.toString() }.toSet()

        // 4. 存储到 SharedPreferences
        with(sharedPreferences.edit()) {
            putStringSet(key, stringSetToSave)
            apply() // 使用 apply 异步提交，提升性能
        }
    }

    /**
     * 检查某个日期是否已签到。
     */
    fun isDayCheckedIn(day: Int): Boolean {
        return getCheckedInDays().contains(day)
    }
}