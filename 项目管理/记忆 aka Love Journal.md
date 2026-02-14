# 节日记忆通知

memory 数据表中 type：festival memory，增加一列：delivered_at：记录这条 memory 以 festive memory 消息类型发送给用户的时间
chat history api 也要做上面的处理
查询 delivered_at 为空的 memory，每次只选 1 条
将该消息作为最新消息提供给 chat history
并落库到 chat history表（隐含的成为最新的消息）
这个解决回到聊天页面时，没有聊天时，也要收到邀请；festival memory 通知消息最为最新的消息，这样用户一定能看到
【先改上面的】chat/completions 查询 delivered_at 为空的 memory，每次只选 1 条，选中后，以 choice=1 的形式发送给 android app
并将该消息写入 chat history，发送时机从 delivered_at 查看
android app 发现有多个 choices，逐一显示、其中为 festival memory 的消息显示为紫色；
并落库到 chat history表；
这个解决在当前页面持续聊天超过 20 条，还能发送通知
festival memory 消息的渐增 ID 要比 AI 回复更大，确保 android app 一定显示（显示最新消息）
【后续】需要删除原有的生成记忆时写入 chat history 的逻辑
