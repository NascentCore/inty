package com.example.firebaselogging

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.firebaselogging.databinding.ActivityMainBinding

/**
 * 主 Activity - Firebase 日志采集示例
 */
class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private lateinit var loggingManager: LoggingManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // 初始化日志管理器
        loggingManager = LoggingManager.getInstance(this)
        
        // 设置日志输出回调
        loggingManager.setLogCallback { message ->
            runOnUiThread {
                appendToLogOutput(message)
            }
        }
        
        // 记录应用启动事件
        loggingManager.logAppOpened()
        
        // 设置按钮点击监听器
        setupClickListeners()
        
        // 初始化日志输出
        appendToLogOutput("[${getCurrentTime()}] Firebase 日志采集示例已启动")
        appendToLogOutput("[${getCurrentTime()}] 请确保已正确配置 google-services.json 文件")
    }
    
    /**
     * 设置按钮点击监听器
     */
    private fun setupClickListeners() {
        // 基础事件记录
        binding.btnLogEvent.setOnClickListener {
            loggingManager.logButtonClick("log_event")
            loggingManager.logEvent("test_event", mapOf(
                "test_parameter" to "test_value",
                "timestamp" to System.currentTimeMillis()
            ))
            showToast("基础事件已记录")
        }
        
        // 测试崩溃
        binding.btnTestCrash.setOnClickListener {
            loggingManager.logButtonClick("test_crash")
            loggingManager.triggerTestCrash()
            showToast("测试崩溃已触发")
        }
        
        // 自定义事件记录
        binding.btnLogCustomEvent.setOnClickListener {
            loggingManager.logButtonClick("log_custom_event")
            val eventName = binding.etEventName.text.toString().ifEmpty { "custom_event" }
            val eventValue = binding.etEventParameter.text.toString().ifEmpty { "test_value" }
            loggingManager.logCustomEvent(eventName, eventValue)
            showToast("自定义事件已记录")
        }
        
        // 设置用户属性
        binding.btnSetUserProperty.setOnClickListener {
            loggingManager.logButtonClick("set_user_property")
            val userId = binding.etUserId.text.toString().ifEmpty { "user_123" }
            val propertyKey = binding.etUserPropertyKey.text.toString().ifEmpty { "user_level" }
            val propertyValue = binding.etUserPropertyValue.text.toString().ifEmpty { "premium" }
            
            loggingManager.setUserId(userId)
            loggingManager.setUserProperty(propertyKey, propertyValue)
            showToast("用户属性已设置")
        }
        
        // 性能监控
        binding.btnLogPerformance.setOnClickListener {
            loggingManager.logButtonClick("log_performance")
            // 模拟一个需要时间的操作
            Thread {
                val startTime = System.currentTimeMillis()
                
                // 模拟一些工作
                Thread.sleep(2000)
                
                val duration = System.currentTimeMillis() - startTime
                loggingManager.logPerformanceEvent("custom_operation", duration)
                
                runOnUiThread {
                    showToast("性能事件已记录")
                }
            }.start()
        }
    }
    
    /**
     * 添加日志到输出区域
     */
    private fun appendToLogOutput(message: String) {
        val currentText = binding.tvLogOutput.text.toString()
        val newText = if (currentText.isEmpty()) {
            message
        } else {
            "$currentText\n$message"
        }
        binding.tvLogOutput.text = newText
        
        // 自动滚动到底部
        binding.tvLogOutput.post {
            val scrollView = binding.tvLogOutput.parent as? android.widget.ScrollView
            scrollView?.fullScroll(android.view.View.FOCUS_DOWN)
        }
    }
    
    /**
     * 显示 Toast 消息
     */
    private fun showToast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }
    
    /**
     * 获取当前时间字符串
     */
    private fun getCurrentTime(): String {
        val sdf = java.text.SimpleDateFormat("HH:mm:ss.SSS", java.util.Locale.getDefault())
        return sdf.format(java.util.Date())
    }
    
    override fun onResume() {
        super.onResume()
        // 记录应用恢复事件
        loggingManager.logEvent("app_resumed", mapOf(
            "timestamp" to System.currentTimeMillis()
        ))
    }
    
    override fun onPause() {
        super.onPause()
        // 记录应用暂停事件
        loggingManager.logEvent("app_paused", mapOf(
            "timestamp" to System.currentTimeMillis()
        ))
    }
}