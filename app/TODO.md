# TODOs

## 结偶聊天管理与角色（智能体）管理

思想：聊天信息应该由角色、用户、历史消息动态组成，不再与角色强关联。

具体来说，调用 `chat/completions` 时，要将相关的信息组合起来、形成提示词，交给大模型回复。
使用缓存保存相关信息，省去频繁查询数据库。

### App 进行变量替代

* 示例：https://github.com/NascentCore/inty/pull/614/files
* 问题：多客户端需要重复实现，如明确的 web 评测和 app

### Backend 进行变量替代，App 仅展示

* 仅支持 {{ char }} {{ user }}，其他内容无法提供对应的 context
* App 须了解如何组合相关数据
