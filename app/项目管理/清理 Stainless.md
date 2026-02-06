# 清理 Stainless

Stainless 生成 SDK 经过实际使用，结论是收效不足以支撑其投入：

1. 节省了定义 API 数据结构

造成的负担：

1. 前后端联调增加了生成 SDK 的步骤，该步骤不能本地完成，且过程中容易出现意外，导致整体流程耗时长、不稳定；打断了前后端联调的顺畅性

其他好处，如自动分页，非常复杂最终没有完全实现

鉴于此，我们决定废弃 Stainless；基本安排如下：

1. 新的 API endpoint 不再使用 Stainless
2. 修改已有的 API endpoint 时，顺手将 Stainless 调用改为原有 HTTP 调用
3. 其他 API endpoint 不需改动则不做修改
