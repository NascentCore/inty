package ai.sxwl.android.utils

import android.annotation.SuppressLint
import android.os.Build
import android.os.Environment
import android.text.TextUtils
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.IOException
import java.io.InputStreamReader
import java.util.Properties

/** ROM工具类 提供ROM相关的工具方法 */
object RomUtils {

    private val ROM_HUAWEI = arrayOf("huawei")
    private val ROM_HARMONY = arrayOf("harmony")
    private val ROM_HONOR = arrayOf("honor")
    private val ROM_VIVO = arrayOf("vivo")
    private val ROM_XIAOMI = arrayOf("xiaomi")
    private val ROM_OPPO = arrayOf("oppo")
    private val ROM_LEECO = arrayOf("leeco", "letv")
    private val ROM_360 = arrayOf("360", "qiku")
    private val ROM_ZTE = arrayOf("zte")
    private val ROM_ONEPLUS = arrayOf("oneplus")
    private val ROM_NUBIA = arrayOf("nubia")
    private val ROM_COOLPAD = arrayOf("coolpad", "yulong")
    private val ROM_LG = arrayOf("lg", "lge")
    private val ROM_GOOGLE = arrayOf("google")
    private val ROM_SAMSUNG = arrayOf("samsung")
    private val ROM_MEIZU = arrayOf("meizu")
    private val ROM_LENOVO = arrayOf("lenovo")
    private val ROM_SMARTISAN = arrayOf("smartisan", "deltainno")
    private val ROM_HTC = arrayOf("htc")
    private val ROM_SONY = arrayOf("sony")
    private val ROM_GIONEE = arrayOf("gionee", "amigo")
    private val ROM_MOTOROLA = arrayOf("motorola")

    private const val VERSION_PROPERTY_HONOR = "ro.honor.build.display.id"
    private const val VERSION_PROPERTY_HARMONY = "hw_sc.build.platform.version"
    private const val VERSION_PROPERTY_HUAWEI = "ro.build.version.emui"
    private const val VERSION_PROPERTY_VIVO = "ro.vivo.os.build.display.id"
    private const val VERSION_PROPERTY_XIAOMI = "ro.build.version.incremental"
    private const val VERSION_PROPERTY_OPPO = "ro.build.version.opporom"
    private const val VERSION_PROPERTY_LEECO = "ro.letv.release.version"
    private const val VERSION_PROPERTY_360 = "ro.build.uiversion"
    private const val VERSION_PROPERTY_ZTE = "ro.build.MiFavor_version"
    private const val VERSION_PROPERTY_ONEPLUS = "ro.rom.version"
    private const val VERSION_PROPERTY_NUBIA = "ro.build.rom.id"
    private const val UNKNOWN = "unknown"

    private var romInfoBean: RomInfo? = null

    /** 是否是华为设备 */
    fun isHuawei(): Boolean {
        return ROM_HUAWEI[0] == getRomInfo().name
    }

    /** 是否是鸿蒙系统 */
    fun isHarmonyOS(): Boolean {
        return ROM_HARMONY[0] == getRomInfo().name
    }

    /** 是否是荣耀设备 */
    fun isHonor(): Boolean {
        return ROM_HONOR[0] == getRomInfo().name
    }

    /** 是否是vivo设备 */
    fun isVivo(): Boolean {
        return ROM_VIVO[0] == getRomInfo().name
    }

    /** 是否是小米设备 */
    fun isXiaomi(): Boolean {
        return ROM_XIAOMI[0] == getRomInfo().name
    }

    /** 是否是OPPO设备 */
    fun isOppo(): Boolean {
        return ROM_OPPO[0] == getRomInfo().name
    }

    /** 是否是乐视设备 */
    fun isLeeco(): Boolean {
        return ROM_LEECO[0] == getRomInfo().name
    }

    /** 是否是360设备 */
    fun is360(): Boolean {
        return ROM_360[0] == getRomInfo().name
    }

    /** 是否是中兴设备 */
    fun isZte(): Boolean {
        return ROM_ZTE[0] == getRomInfo().name
    }

    /** 是否是一加设备 */
    fun isOneplus(): Boolean {
        return ROM_ONEPLUS[0] == getRomInfo().name
    }

    /** 是否是努比亚设备 */
    fun isNubia(): Boolean {
        return ROM_NUBIA[0] == getRomInfo().name
    }

    /** 是否是酷派设备 */
    fun isCoolpad(): Boolean {
        return ROM_COOLPAD[0] == getRomInfo().name
    }

    /** 是否是LG设备 */
    fun isLg(): Boolean {
        return ROM_LG[0] == getRomInfo().name
    }

    /** 是否是Google设备 */
    fun isGoogle(): Boolean {
        return ROM_GOOGLE[0] == getRomInfo().name
    }

    /** 是否是三星设备 */
    fun isSamsung(): Boolean {
        return ROM_SAMSUNG[0] == getRomInfo().name
    }

    /** 是否是魅族设备 */
    fun isMeizu(): Boolean {
        return ROM_MEIZU[0] == getRomInfo().name
    }

    /** 是否是联想设备 */
    fun isLenovo(): Boolean {
        return ROM_LENOVO[0] == getRomInfo().name
    }

    /** 是否是锤子设备 */
    fun isSmartisan(): Boolean {
        return ROM_SMARTISAN[0] == getRomInfo().name
    }

    /** 是否是HTC设备 */
    fun isHtc(): Boolean {
        return ROM_HTC[0] == getRomInfo().name
    }

    /** 是否是索尼设备 */
    fun isSony(): Boolean {
        return ROM_SONY[0] == getRomInfo().name
    }

    /** 是否是金立设备 */
    fun isGionee(): Boolean {
        return ROM_GIONEE[0] == getRomInfo().name
    }

    /** 是否是摩托罗拉设备 */
    fun isMotorola(): Boolean {
        return ROM_MOTOROLA[0] == getRomInfo().name
    }

    /** 获取ROM信息 */
    fun getRomInfo(): RomInfo {
        if (romInfoBean != null) return romInfoBean!!

        romInfoBean = RomInfo()
        val brand = getBrand()
        val manufacturer = getManufacturer()

        when {
            isRightRom(brand, manufacturer, *ROM_HUAWEI) -> {
                romInfoBean!!.name = ROM_HUAWEI[0]
                var version = getRomVersion(VERSION_PROPERTY_HUAWEI)
                val temp = version.split("_")
                romInfoBean!!.version = if (temp.size > 1) temp[1] else version
                return romInfoBean!!
            }
            checkIsHarmonyOs() -> {
                romInfoBean!!.name = ROM_HARMONY[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_HARMONY)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_HONOR) -> {
                romInfoBean!!.name = ROM_HONOR[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_HONOR)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_VIVO) -> {
                romInfoBean!!.name = ROM_VIVO[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_VIVO)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_XIAOMI) -> {
                romInfoBean!!.name = ROM_XIAOMI[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_XIAOMI)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_OPPO) -> {
                romInfoBean!!.name = ROM_OPPO[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_OPPO)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_LEECO) -> {
                romInfoBean!!.name = ROM_LEECO[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_LEECO)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_360) -> {
                romInfoBean!!.name = ROM_360[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_360)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_ZTE) -> {
                romInfoBean!!.name = ROM_ZTE[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_ZTE)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_ONEPLUS) -> {
                romInfoBean!!.name = ROM_ONEPLUS[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_ONEPLUS)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_NUBIA) -> {
                romInfoBean!!.name = ROM_NUBIA[0]
                romInfoBean!!.version = getRomVersion(VERSION_PROPERTY_NUBIA)
                return romInfoBean!!
            }
            isRightRom(brand, manufacturer, *ROM_COOLPAD) -> {
                romInfoBean!!.name = ROM_COOLPAD[0]
            }
            isRightRom(brand, manufacturer, *ROM_LG) -> {
                romInfoBean!!.name = ROM_LG[0]
            }
            isRightRom(brand, manufacturer, *ROM_GOOGLE) -> {
                romInfoBean!!.name = ROM_GOOGLE[0]
            }
            isRightRom(brand, manufacturer, *ROM_SAMSUNG) -> {
                romInfoBean!!.name = ROM_SAMSUNG[0]
            }
            isRightRom(brand, manufacturer, *ROM_MEIZU) -> {
                romInfoBean!!.name = ROM_MEIZU[0]
            }
            isRightRom(brand, manufacturer, *ROM_LENOVO) -> {
                romInfoBean!!.name = ROM_LENOVO[0]
            }
            isRightRom(brand, manufacturer, *ROM_SMARTISAN) -> {
                romInfoBean!!.name = ROM_SMARTISAN[0]
            }
            isRightRom(brand, manufacturer, *ROM_HTC) -> {
                romInfoBean!!.name = ROM_HTC[0]
            }
            isRightRom(brand, manufacturer, *ROM_SONY) -> {
                romInfoBean!!.name = ROM_SONY[0]
            }
            isRightRom(brand, manufacturer, *ROM_GIONEE) -> {
                romInfoBean!!.name = ROM_GIONEE[0]
            }
            isRightRom(brand, manufacturer, *ROM_MOTOROLA) -> {
                romInfoBean!!.name = ROM_MOTOROLA[0]
            }
            else -> {
                romInfoBean!!.name = manufacturer
            }
        }

        romInfoBean!!.version = getRomVersion("")
        return romInfoBean!!
    }

    private fun isRightRom(brand: String, manufacturer: String, vararg names: String): Boolean {
        for (name in names) {
            if (brand.contains(name) || manufacturer.contains(name)) {
                return true
            }
        }
        return false
    }

    /** 检查是否为鸿蒙系统 */
    private fun checkIsHarmonyOs(): Boolean {
        return try {
            val buildExClass = Class.forName("com.huawei.system.BuildEx")
            val osBrand = buildExClass.getMethod("getOsBrand").invoke(buildExClass)
            osBrand != null && ROM_HARMONY[0].equals(osBrand.toString(), ignoreCase = true)
        } catch (ignore: Throwable) {
            false
        }
    }

    private fun getManufacturer(): String {
        return try {
            val manufacturer = Build.MANUFACTURER
            if (!TextUtils.isEmpty(manufacturer)) {
                manufacturer.lowercase()
            } else {
                UNKNOWN
            }
        } catch (ignore: Throwable) {
            UNKNOWN
        }
    }

    private fun getBrand(): String {
        return try {
            val brand = Build.BRAND
            if (!TextUtils.isEmpty(brand)) {
                brand.lowercase()
            } else {
                UNKNOWN
            }
        } catch (ignore: Throwable) {
            UNKNOWN
        }
    }

    private fun getRomVersion(propertyName: String): String {
        var ret = ""
        if (!TextUtils.isEmpty(propertyName)) {
            ret = getSystemProperty(propertyName)
        }
        if (TextUtils.isEmpty(ret) || ret == UNKNOWN) {
            try {
                val display = Build.DISPLAY
                if (!TextUtils.isEmpty(display)) {
                    ret = display.lowercase()
                }
            } catch (ignore: Throwable) {
                // ignore
            }
        }
        return if (TextUtils.isEmpty(ret)) UNKNOWN else ret
    }

    private fun getSystemProperty(name: String): String {
        var prop = getSystemPropertyByShell(name)
        if (!TextUtils.isEmpty(prop)) return prop
        prop = getSystemPropertyByStream(name)
        if (!TextUtils.isEmpty(prop)) return prop
        return if (Build.VERSION.SDK_INT < 28) {
            getSystemPropertyByReflect(name)
        } else {
            prop
        }
    }

    private fun getSystemPropertyByShell(propName: String): String {
        var input: BufferedReader? = null
        var process: Process? = null
        return try {
            process = Runtime.getRuntime().exec("getprop $propName")
            input = BufferedReader(InputStreamReader(process.inputStream), 1024)
            val ret = input.readLine()
            ret ?: ""
        } catch (ignore: IOException) {
            ""
        } finally {
            try {
                input?.close()
            } catch (ignore: IOException) {
                // ignore
            }
            try {
                process?.destroy()
            } catch (ignore: Exception) {
                // ignore
            }
        }
    }

    private fun getSystemPropertyByStream(key: String): String {
        var inputStream: FileInputStream? = null
        return try {
            val prop = Properties()
            val rootDir: File? = Environment.getRootDirectory()
            if (rootDir != null) {
                inputStream = FileInputStream(File(rootDir, "build.prop"))
                prop.load(inputStream)
                prop.getProperty(key, "")
            } else {
                ""
            }
        } catch (ignore: Exception) {
            ""
        } finally {
            try {
                inputStream?.close()
            } catch (ignore: Exception) {
                // ignore
            }
        }
    }

    @SuppressLint("PrivateApi")
    private fun getSystemPropertyByReflect(key: String): String {
        return try {
            val clz = Class.forName("android.os.SystemProperties")
            val getMethod = clz.getMethod("get", String::class.java, String::class.java)
            val result = getMethod.invoke(clz, key, "")
            result as? String ?: ""
        } catch (ignore: Exception) {
            ""
        }
    }

    /** ROM信息数据类 */
    data class RomInfo(var name: String = "", var version: String = "") {
        override fun toString(): String {
            return "RomInfo{name=$name, version=$version}"
        }
    }

    // 保留原有的便捷方法，保持向后兼容
    /** 获取ROM名称 */
    fun getRomName(): String {
        return getRomInfo().name
    }

    /** 获取ROM版本 */
    fun getRomVersion(): String {
        return getRomInfo().version
    }

    /** 检查是否为MIUI */
    fun isMIUI(): Boolean {
        return isXiaomi()
    }

    /** 检查是否为EMUI */
    fun isEMUI(): Boolean {
        return isHuawei()
    }

    /** 检查是否为ColorOS */
    fun isColorOS(): Boolean {
        return isOppo()
    }

    /** 检查是否为FuntouchOS */
    fun isFuntouchOS(): Boolean {
        return isVivo()
    }

    /** 检查是否为Flyme */
    fun isFlyme(): Boolean {
        return isMeizu()
    }

    /** 检查是否为SmartisanOS */
    fun isSmartisanOS(): Boolean {
        return isSmartisan()
    }

    /** 检查是否为OneUI */
    fun isOneUI(): Boolean {
        return isSamsung()
    }

    /** 检查是否为AOSP */
    fun isAOSP(): Boolean {
        return isGoogle()
    }
}
