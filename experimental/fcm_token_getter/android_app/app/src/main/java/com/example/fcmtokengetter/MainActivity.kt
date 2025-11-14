package com.example.fcmtokengetter

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {

    private val tokenService = TokenService()
    private var currentToken: String? = null

    private lateinit var statusText: TextView
    private lateinit var tokenText: TextView
    private lateinit var baseUrlInput: EditText
    private lateinit var authTokenInput: EditText
    private lateinit var getTokenButton: Button
    private lateinit var copyTokenButton: Button
    private lateinit var registerButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 确保通知渠道已创建
        NotificationChannels.ensureDefaultChannel(this)

        // Android 13+ 需要请求通知权限
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    1001
                )
            }
        }

        initViews()
        setupClickListeners()

        // 初始化时自动获取 token
        getToken()
    }

    private fun initViews() {
        statusText = findViewById(R.id.status_text)
        tokenText = findViewById(R.id.token_text)
        baseUrlInput = findViewById(R.id.base_url_input)
        authTokenInput = findViewById(R.id.auth_token_input)
        getTokenButton = findViewById(R.id.get_token_button)
        copyTokenButton = findViewById(R.id.copy_token_button)
        registerButton = findViewById(R.id.register_button)

        // 设置默认值
        baseUrlInput.setText(ServerConfig.BASE_URL)
    }

    private fun setupClickListeners() {
        getTokenButton.setOnClickListener {
            getToken()
        }

        copyTokenButton.setOnClickListener {
            copyTokenToClipboard()
        }

        registerButton.setOnClickListener {
            registerToken()
        }
    }

    private fun getToken() {
        statusText.text = "正在获取 FCM Token..."
        getTokenButton.isEnabled = false

        lifecycleScope.launch {
            val token = withContext(Dispatchers.IO) {
                tokenService.getFCMToken()
            }

            if (token != null) {
                currentToken = token
                tokenText.text = token
                statusText.text = "FCM Token 获取成功"
                copyTokenButton.isEnabled = true
                registerButton.isEnabled = true
            } else {
                statusText.text = "获取 FCM Token 失败，请检查 Firebase 配置"
                tokenText.text = ""
                copyTokenButton.isEnabled = false
                registerButton.isEnabled = false
            }

            getTokenButton.isEnabled = true
        }
    }

    private fun copyTokenToClipboard() {
        val token = currentToken
        if (token.isNullOrBlank()) {
            Toast.makeText(this, "没有可复制的 Token", Toast.LENGTH_SHORT).show()
            return
        }

        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("FCM Token", token)
        clipboard.setPrimaryClip(clip)
        Toast.makeText(this, "Token 已复制到剪贴板", Toast.LENGTH_SHORT).show()
    }

    private fun registerToken() {
        val token = currentToken
        if (token.isNullOrBlank()) {
            Toast.makeText(this, "请先获取 Token", Toast.LENGTH_SHORT).show()
            return
        }

        val baseUrl = baseUrlInput.text.toString().trim()
        if (baseUrl.isBlank()) {
            Toast.makeText(this, "请输入后端 API 地址", Toast.LENGTH_SHORT).show()
            return
        }

        val authToken = authTokenInput.text.toString().trim()
        if (authToken.isBlank()) {
            Toast.makeText(this, "请输入认证 Token", Toast.LENGTH_SHORT).show()
            return
        }

        statusText.text = "正在注册 Token 到服务器..."
        registerButton.isEnabled = false

        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                tokenService.registerTokenToServer(token, authToken, baseUrl)
            }

            when (result) {
                is TokenService.RegisterResult.Success -> {
                    statusText.text = result.message
                    Toast.makeText(this@MainActivity, result.message, Toast.LENGTH_SHORT).show()
                }
                is TokenService.RegisterResult.Error -> {
                    statusText.text = result.message
                    Toast.makeText(this@MainActivity, result.message, Toast.LENGTH_LONG).show()
                }
            }

            registerButton.isEnabled = true
        }
    }
}

