package ai.sxwl.android.data.store

import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey

/**
 * DataStore 键值定义
 * 集中管理所有的 PreferencesKey，避免重复定义和键值冲突
 */
object DataStoreKeys {

    /**
     * 用户相关键值
     */
    object User {
        //当前登录状态的用户的uid，可以是guest，可以是正式uid，若为空，则为未登录状态
        val CURRENT_USER_ID = stringPreferencesKey("current_use_id")
        val CURRENT_USER_TOKEN = stringPreferencesKey("current_use_token")
        val CURRENT_USER_INFO = stringPreferencesKey("current_use_info")
        val IS_GUEST = booleanPreferencesKey("is_guest")

        //该设备的guest信息
        val GUEST_ID = stringPreferencesKey("guest_id")
        val GUEST_TOKEN = stringPreferencesKey("guest_token")
        val GUEST_USER_INFO_JSON = stringPreferencesKey("guest_user_info_json")

        //正式用户相关的标记
        val USER_ID = stringPreferencesKey("user_id")
        val USER_TOKEN = stringPreferencesKey("user_token")
        val USER_INFO_JSON = stringPreferencesKey("user_info_json")

        val IS_VIP = booleanPreferencesKey("is_vip")
        val VIP_EXPIRE_TIME = longPreferencesKey("vip_expire_time")
        val LAST_LOGIN_TIME = longPreferencesKey("last_login_time")
    }

    /**
     * 应用相关键值
     */
    object App {
        val API_BASE_URL = stringPreferencesKey("api_base_url")

    }

    /**
     * 设备相关键值
     */
    object Device {
        val DEVICE_ID = stringPreferencesKey("device_id")
        val ANDROID_ID = stringPreferencesKey("android_id")

    }

    /**
     * 聊天相关键值
     */
    object Chat {

    }

    /**
     * AI相关键值
     */
    object Ai {

    }
}
