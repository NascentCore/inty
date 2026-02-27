# 后端迁移到使用 IM 进行 app-后端通信

@李远 现在 app 计划提供长链接、从而让 AI 能主动发消息给用户、同时打破 1 问 1 答到交互方式，目的是提高 AI 的“活人感”

技术路线上有 2 个选择：
接一个第三方的 IM 云服务（目前倾向于 https://netease.im/、现在的安卓主程有经验）
自己维护 ws 长链接（这个以前已经做过语音通话、也有经验）

按你之前的经验、点评一下？[双手合十]

https://applink.feishu.cn/client/message/link/open?token=Amiinj%2BhakAEaZ5x2BLATMQ%3D
https://applink.feishu.cn/client/message/link/open?token=Amiinj%2BhakAEaZ5x3RFBjN0%3D

@学宝
https://applink.feishu.cn/client/message/link/open?token=AmkX08%2BiwAy9aZ5x5KcBDNY%3D

类似问题是否在 IM 系统更容易解决：

- https://applink.feishu.cn/client/message/link/open?token=AmfpyocKAMADaZ5x%2FXJBTNU%3D

- [ ] 生图耗时过长，在应用层面比较难控制线性执行
