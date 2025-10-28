1. message_send_success是发送消息并且服务器正确返回的事件。（不区分是否触发次数限制，vip限制等）
1. chat_session_start在app端和后端都有打点。app端的用意是开始渲染当前聊天界面，但目前看上报时机会冗余，不够精准。
1. free_limit_reached这个是免费用发送消息后，触发了接口返回次数限制的时候上报。1. 另有app_start（启动App时）
1. chat_session_end退出聊天界面（时机可能不够精准）
1. message_sent 是点击发送后，真正触发接口发送时的打点
1. message_send_failure 消息发送接口返回失败
1. explore_page_view 是Explore页面的开始展示以上是线上版本的一些点位。