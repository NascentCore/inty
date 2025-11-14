package com.example.fcmtokengetter

object ServerConfig {
    /**
     * 后端 API 基础地址
     * Android 模拟器访问宿主机的默认地址为 http://10.0.2.2:8000
     * 真机调试时需改为电脑局域网 IP 或后端公网地址
     */
    var BASE_URL = "http://10.0.2.2:8000"

    /**
     * 设备 token 注册接口路径
     */
    const val REGISTER_DEVICE_TOKEN_PATH = "/api/v1/users/device/register"
}


