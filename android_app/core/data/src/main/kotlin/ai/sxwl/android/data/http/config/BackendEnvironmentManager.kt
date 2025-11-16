package ai.sxwl.android.data.http.config

// CREATED_BY_AGENT

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.os.FileObserver
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONArray
import org.json.JSONObject

/**
 * 运行时后端环境管理器，通过可编辑的 JSON 配置文件映射不同构建类型到具体的后端地址。
 *
 * 配置来源优先级：
 * 1. 应用私有目录中的运行时配置（可通过 adb / Device File Explorer 无需重新编译修改）
 * 2. assets 中的默认配置（首次启动会复制到私有目录）
 * 3. 代码内置的常量兜底
 */
object BackendEnvironmentManager {

    private const val TAG = "BackendEnvironmentManager"
    private const val DEFAULT_ASSET_FILE = "backend_endpoints.defaults.json"
    private const val CONFIG_DIRECTORY = "config"
    private const val CONFIG_FILE_NAME = "backend_endpoints.json"
    private const val CREATED_BY_AGENT_KEY = "CREATED_BY_AGENT"

    private val lock = Any()
    private val state = AtomicReference(fallbackState())
    private var appContext: Context? = null
    private var isInitialized = false
    private var fileObserver: FileObserver? = null

    data class BackendEnvironment(
        val id: String,
        val baseUrl: String,
        val notes: String? = null,
    )

    private data class BackendState(
        val environments: Map<String, BackendEnvironment>,
        val aliasIndex: Map<String, BackendEnvironment>,
        val defaultEnvId: String,
        val buildTypeOverrides: Map<String, String>,
    )

    /**
     * 初始化运行时配置，确保配置文件就绪并启动文件观察。
     */
    fun initialize(context: Context) {
        synchronized(lock) {
            if (isInitialized) {
                return
            }
            appContext = context.applicationContext
            val runtimeFile = ensureRuntimeConfigFile()
            loadConfigFromDisk(runtimeFile)
            startWatching(runtimeFile)
            isInitialized = true
            LogUtils.i(TAG, "初始化完成，已加载 ${state.get().environments.size} 个后端环境")
        }
    }

    /**
     * 获取指定构建类型的基础 URL；如配置缺失则返回 null，调用方需处理兜底。
     */
    fun getBaseUrlFor(buildType: String): String? {
        val snapshot = state.get()
        val normalizedKey = buildType.lowercase()
        val envId = snapshot.buildTypeOverrides[normalizedKey] ?: snapshot.defaultEnvId
        val environment =
            envId?.let { snapshot.environments[it] }
                ?: snapshot.aliasIndex[normalizedKey]

        return environment?.baseUrl
    }

    /**
     * 返回当前所有可用环境列表，用于调试或设置界面展示。
     */
    fun getAvailableBackends(): List<BackendEnvironment> = state.get().environments.values.toList()

    /**
     * 手动刷新配置（例如开发者设置页面调用）。
     */
    fun refresh() {
        synchronized(lock) {
            val runtimeFile = ensureRuntimeConfigFile()
            loadConfigFromDisk(runtimeFile)
        }
    }

    private fun ensureRuntimeConfigFile(): File {
        val context =
            appContext
                ?: throw IllegalStateException("BackendEnvironmentManager is not initialized yet.")
        val configDir = File(context.filesDir, CONFIG_DIRECTORY)
        if (!configDir.exists() && !configDir.mkdirs()) {
            LogUtils.w(TAG, "无法创建配置目录：${configDir.absolutePath}")
        }
        val configFile = File(configDir, CONFIG_FILE_NAME)
        if (!configFile.exists()) {
            copyDefaultConfig(configFile)
        }
        return configFile
    }

    private fun copyDefaultConfig(targetFile: File) {
        val context = appContext ?: return
        try {
            context.assets.open(DEFAULT_ASSET_FILE).use { input ->
                FileOutputStream(targetFile).use { output -> input.copyTo(output) }
            }
            LogUtils.i(TAG, "已复制默认后端配置到 ${targetFile.absolutePath}")
        } catch (assetError: IOException) {
            LogUtils.w(TAG, "复制默认配置失败，退回内置常量：${assetError.message}")
            // 尝试写入内置兜底配置
            runCatching {
                FileOutputStream(targetFile).use { output ->
                    output.write(buildFallbackJson().toByteArray())
                }
            }
        }
    }

    private fun startWatching(configFile: File) {
        fileObserver?.stopWatching()
        fileObserver =
            object :
                FileObserver(
                    configFile.absolutePath,
                    CLOSE_WRITE or ATTRIB or MOVED_TO or DELETE_SELF or MOVE_SELF,
                ) {
                override fun onEvent(event: Int, path: String?) {
                    when (event) {
                        DELETE_SELF,
                        MOVE_SELF,
                        -> {
                            LogUtils.w(TAG, "配置文件被删除或移动，重新创建")
                            synchronized(lock) {
                                val runtimeFile = ensureRuntimeConfigFile()
                                loadConfigFromDisk(runtimeFile)
                                startWatching(runtimeFile)
                            }
                        }
                        else -> {
                            LogUtils.d(TAG, "检测到配置变更，重新加载")
                            refresh()
                        }
                    }
                }
            }.also { it.startWatching() }
    }

    private fun loadConfigFromDisk(file: File) {
        val newState =
            runCatching {
                val content = file.readText()
                parseConfig(content)
            }.getOrElse { error ->
                LogUtils.w(TAG, "解析运行时配置失败，退回内置配置：${error.message}")
                fallbackState()
            }
        state.set(newState)
        LogUtils.i(
            TAG,
            "已加载运行时配置：${newState.environments.size} 个环境，默认=${newState.defaultEnvId}",
        )
    }

    private fun parseConfig(raw: String): BackendState {
        val root = JSONObject(raw)
        if (!root.has(CREATED_BY_AGENT_KEY)) {
            LogUtils.d(TAG, "运行时配置缺少 CREATED_BY_AGENT 标记，仍尝试解析")
        }
        val envArray = root.optJSONArray("backends") ?: JSONArray()
        val environments = mutableMapOf<String, BackendEnvironment>()
        val aliasIndex = mutableMapOf<String, BackendEnvironment>()

        for (index in 0 until envArray.length()) {
            val envJson = envArray.optJSONObject(index) ?: continue
            val id = envJson.optString("id").takeIf { it.isNotBlank() } ?: continue
            val baseUrl =
                normalizeBaseUrl(envJson.optString("base_url")) ?: continue
            val environment =
                BackendEnvironment(
                    id = id,
                    baseUrl = baseUrl,
                    notes = envJson.optString("notes").ifBlank { null },
                )
            environments[id] = environment
            aliasIndex[id.lowercase()] = environment
        }

        if (environments.isEmpty()) {
            throw IllegalStateException("未在配置中找到有效后端环境")
        }

        val overrides =
            root.optJSONObject("build_type_overrides")?.let { overridesJson ->
                buildMap {
                    overridesJson.keys().forEach { key ->
                        val envId = overridesJson.optString(key)
                        if (envId.isNotBlank()) {
                            put(key.lowercase(), envId)
                        }
                    }
                }
            } ?: emptyMap()

        val defaultEnvId =
            root.optString("default_backend").takeIf { it.isNotBlank() }
                ?: environments.keys.first()

        return BackendState(
            environments = environments,
            aliasIndex = aliasIndex,
            defaultEnvId = defaultEnvId,
            buildTypeOverrides = overrides,
        )
    }

    private fun normalizeBaseUrl(url: String): String? {
        if (url.isBlank()) {
            return null
        }
        val trimmed = url.trim()
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
            LogUtils.w(TAG, "忽略无效 URL（缺少协议）：$trimmed")
            return null
        }
        return if (trimmed.endsWith("/")) trimmed else "$trimmed/"
    }

    private fun fallbackState(): BackendState {
        val prod =
            BackendEnvironment(
                id = "prod",
                baseUrl = "https://${Constant.USER_HOST}/",
            )
        val dev =
            BackendEnvironment(
                id = "dev",
                baseUrl = "https://${Constant.USER_HOST_DEV}/",
            )
        val local =
            BackendEnvironment(
                id = "local",
                baseUrl = "http://${Constant.USER_HOST_LOCAL}/",
            )
        val environments =
            mapOf(prod.id to prod, dev.id to dev, local.id to local)
        val aliasIndex =
            buildMap {
                put(prod.id, prod)
                put("release", prod)
                put(dev.id, dev)
                put("debug", dev)
                put("playdebug", dev)
                put(local.id, local)
                put("localhost", local)
            }.mapKeys { it.key.lowercase() }

        val overrides =
            mapOf(
                "local" to local.id,
                "debug" to dev.id,
                "playdebug" to dev.id,
                "release" to prod.id,
            )

        return BackendState(
            environments = environments,
            aliasIndex = aliasIndex,
            defaultEnvId = prod.id,
            buildTypeOverrides = overrides,
        )
    }

    private fun buildFallbackJson(): String {
        val root =
            JSONObject()
                .put(CREATED_BY_AGENT_KEY, "cursor")
                .put("schema_version", 1)
                .put("default_backend", "prod")
                .put(
                    "build_type_overrides",
                    JSONObject(
                        mapOf(
                            "local" to "local",
                            "debug" to "dev",
                            "playdebug" to "dev",
                            "release" to "prod",
                        ),
                    ),
                )
        val backends =
            JSONArray()
                .put(
                    JSONObject()
                        .put("id", "prod")
                        .put("base_url", "https://${Constant.USER_HOST}/"),
                )
                .put(
                    JSONObject()
                        .put("id", "dev")
                        .put("base_url", "https://${Constant.USER_HOST_DEV}/"),
                )
                .put(
                    JSONObject()
                        .put("id", "local")
                        .put("base_url", "http://${Constant.USER_HOST_LOCAL}/"),
                )
        root.put("backends", backends)
        return root.toString(2)
    }
}
