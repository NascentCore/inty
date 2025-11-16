package ai.sxwl.android.data.http.config

// CREATED_BY_AGENT

import java.lang.reflect.InvocationTargetException
import java.util.concurrent.atomic.AtomicReference
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class BackendEnvironmentManagerTest {

    private val manager = BackendEnvironmentManager
    private val managerClass = BackendEnvironmentManager::class.java
    private val parseMethod =
        managerClass.getDeclaredMethod("parseConfig", String::class.java).apply {
            isAccessible = true
        }
    private val fallbackMethod = managerClass.getDeclaredMethod("fallbackState").apply {
        isAccessible = true
    }
    private val stateField = managerClass.getDeclaredField("state").apply { isAccessible = true }

    @After fun tearDown() { resetToFallback() }

    @Test
    fun getBaseUrlFor_respectsOverridesAndDefaultBackend() {
        val configJson =
            """
            {
              "CREATED_BY_AGENT": "cursor",
              "default_backend": "qa",
              "build_type_overrides": {
                "release": "prod",
                "debug": "dev"
              },
              "backends": [
                { "id": "prod", "base_url": "https://prod.inty.cc" },
                { "id": "qa", "base_url": "https://qa.inty.cc/" },
                { "id": "dev", "base_url": "https://dev.inty.cc" }
              ]
            }
            """.trimIndent()

        val backendState = invokeParse(configJson)
        setInternalState(backendState)

        assertEquals(
            "https://prod.inty.cc/",
            manager.getBaseUrlFor("release"),
            "release 覆盖应指向生产端点",
        )
        assertEquals(
            "https://dev.inty.cc/",
            manager.getBaseUrlFor("debug"),
            "debug 覆盖应指向 dev 端点",
        )
        assertEquals(
            "https://qa.inty.cc/",
            manager.getBaseUrlFor("playdebug"),
            "未显式覆盖的构建类型应使用 default_backend",
        )
    }

    @Test
    fun parseConfig_withoutBackends_throws() {
        val invalidJson =
            """
            {
              "CREATED_BY_AGENT": "cursor",
              "default_backend": "prod",
              "backends": []
            }
            """.trimIndent()

        assertThrows(IllegalStateException::class.java) { invokeParse(invalidJson) }
    }

    private fun invokeParse(raw: String): Any {
        return try {
            parseMethod.invoke(manager, raw)
        } catch (error: InvocationTargetException) {
            throw error.targetException
        }
    }

    private fun setInternalState(newState: Any) {
        @Suppress("UNCHECKED_CAST")
        val atomic = stateField.get(manager) as AtomicReference<Any>
        atomic.set(newState)
    }

    private fun resetToFallback() {
        val fallbackState = fallbackMethod.invoke(manager)
        setInternalState(fallbackState)
    }
}
