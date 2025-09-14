# InTy API 文档

## 规范

- 所有接口的响应都遵循统一的格式：
  - code: 状态码，200 表示成功
  - message: 状态描述
  - data: 具体的业务数据
- 对于分页接口，统一包含：
  - code: 状态码，200 表示成功
  - message: 状态描述
  - data: 具体的业务数据
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页大小
    - total_pages: 总页数
    - list: 具体数据列表