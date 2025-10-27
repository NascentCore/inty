# 动态调整后端 URL 不用重新编译，直接运行时修改（或者只需要可以忽略的时间）

在测试中需要调用本地后端服务，方便测试端到端功能。
但是目前指向后端的配置 URL 是根据 build type 动态设置，每次修改需要重新编译（缓存无效）。
本设计旨在提供实时修改后端 api 地址的方法。

# 方案：

1. 现统一原有的网络库network的使用，和inty sdk的网络库的okhttp的client
2. 对buildType（现有debug、playdebug、release和local）不同配置url
3. 对第一点已经统一后的client配置动态baseUrl，通过缓存文件形式保存，并在app启动配置阶段生效
4. 创建一个非release可以使用的依赖模块和UI功能，用于切换BaseUrl
