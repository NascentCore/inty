# Gemini CLI 说明

除非明确指示，否则请遵循以下说明

＃＃ 一般的

- 简洁
- 永远奔跑`npm run lint:format`在提交更改之前
- 始终prefer使用更新版本的库/工具
- 当有多个选项时，实施最好的一个，不要尝试添加多个选项
  例如，如果有 3 种方式启动应用程序`npm run` `docker` `docker compose`只需使用`npm run`- 假设开发模式，这意味着密切跟踪变化

## 高级文档

- 所有文档均为 Markdown 格式
- 新的 Markdown 文件名必须全部大写字母和“\_”，带有“.md”后缀
  不要重命名现有的 Markdown 文件
- 生成新的 markdown 文件时，始终使用 prepend 'GEMINI\_' prefix 来区分工具
- 编写注释时，始终 prepend 注释文本带有“GEMINI：”以表明它们是由 Gemini cli 生成的
- 根据以下markdown文件的描述来决定在哪里读写文档- README.md：该文件夹下所有内容实现的工具用户说明
  - 开发。md：针对此文件夹下所有内容的开发人员和维护人员的说明