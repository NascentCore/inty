package com.ai.intellimate

import android.content.Intent
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.BySelector
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ScriptedClickTest {
    companion object {
        private const val LAUNCH_TIMEOUT_MS: Long = 5_000
        private const val ACTION_TIMEOUT_MS: Long = 3_000
    }

    @Test
    fun scripted_clicks() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val packageName = context.packageName
        val device = UiDevice.getInstance(instrumentation)

        device.pressHome()

        val intent =
            context.packageManager.getLaunchIntentForPackage(packageName)?.apply {
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK)
            }
        requireNotNull(intent) { "Launch intent not found for package: $packageName" }
        context.startActivity(intent)

        device.wait(Until.hasObject(By.pkg(packageName).depth(0)), LAUNCH_TIMEOUT_MS)

        val steps: List<Step> =
            listOf(
                Wait(1000),
                ClickText("允许"),
                ClickText("Allow"),
                ClickText("OK"),
                ClickDesc("Navigate up"),
                Back,
            )

        runSteps(device, steps, packageName)
    }

    private fun runSteps(
        device: UiDevice,
        steps: List<Step>,
        packageName: String,
    ) {
        for (step in steps) {
            when (step) {
                is Wait -> SystemClock.sleep(step.ms)
                Back -> device.pressBack()
                is ClickText -> clickWithFallback(device, By.text(step.text))
                is ClickDesc -> clickWithFallback(device, By.desc(step.desc))
                is ClickResId -> clickWithFallback(device, By.res(packageName, step.resId))
            }
        }
    }

    private fun clickWithFallback(
        device: UiDevice,
        selector: BySelector,
        timeoutMs: Long = ACTION_TIMEOUT_MS,
    ) {
        val obj = device.wait(Until.findObject(selector), timeoutMs)
        obj?.click()
    }
}

sealed interface Step

data class ClickText(val text: String) : Step

data class ClickDesc(val desc: String) : Step

data class ClickResId(val resId: String) : Step

data class Wait(val ms: Long) : Step

object Back : Step
