# Inty 长期 AI 陪伴（仓库总入口 AGENTS.md）

## 概述

- IntelliMate 定位为面向 35+、有较好社会地位与自我认知的美国男性用户的长期 AI 陪伴产品，提供可持续进化的情感陪伴。
- IntelliMate 产品形态基于 Chat 界面，用户通过手机屏幕、与 iMate 交流，使用文字、图片、
声音（语音消息、通话、音乐）、视频（动图、视频、背景声音等）。
  - iMate 是所有角色的总称，如”这是为您推荐的 iMates“。
  - iMate 是提供情感陪伴体验的主体，IntelliMate 无法通过人工设计来满足用户需求，只能通过 iMate 让用户通过与其互动来持续获得和优化的情感陪伴体验
  - Character/Agent/iMate 通常指同一概念，Agent 沿用自后端、指一个独立的逻辑概念来指代一个独立的抽象角色
  - Character（角色）沿用自业界的统称，一般来自 Character.ai
- **用户手册**：IntelliMate Android App 内用户可见的改动都要对应更新[用户手册](docs/INTELLIMATE.md)
  - app/（后端）改动不改动[用户手册](docs/INTELLIMATE.md)
  - 使用 jinja2 template 编写提示词模版：`{{ <变量名> }}`
    使用 `prompt_template.py:render_prompt_jinja2_template` 来生成最终提示词
    - 生产环境代码禁止使用 python `f""` 字符串、测试中可以使用

## 代码库内的一般性约定

- **语言**：
  - Must use English for texts viewable to public users
  - 所有可自然语言表达的输出统一使用中文（普通话）。代码、命令、标识符不受该限制。
    只包含文档的目录用中文命名、方便理解，包含代码的目录必须用 English 以方便调用。
    - 如有可能、在不影响正确性前提下，使用中文编写各类非代码的文字内容：代码注释、GitHub Pull Request 标题 & 描述等等
    - 本代码库开发人员母语为中文普通话
    - 该指令仅适用于可以使用中文的场景；若内容不能使用中文（如代码），则不适用。
- **评测数据**:
  - 采集要放在功能开发的核心需求里：原始数据收集（在功能设计过程中可以考虑将重要数据写入日志、数据库）、数据筛选清洗等等

## 软件工程规范

- **代码结构规范**
  1. Functions should be composable, prefer `func a(), func b(), func c() { a(); b() }`
     over `func a(), func b() { a() }, func c() { b() }`.
     Avoid deep nesting of funcation calls.
  2. Always define types to name input and output, and cleanly separate the codd reading
     input and writing output, with the abstract data processing and handling that can
     work with abstract data types. Example:
     prefer `def write_to_db(data, db) { ... }; def read_from_db() { ... }; def proc() { }` over `def proc() { code reading from db, processing, code writing to db}`
- **TDD**：采用测试驱动开发方式，首先编写测试来预演目标行为，然后通过迭代代码来使测试通过
  - 使用单元测试作为代码的“可执行规范”，通过测试用例来体现设计目标
  - 使用单元测试作为代码行为的“可执行示例”，通过测试用例来提供具体的代码行为描述
- **优先可维护性**：避免“为了省事”引入隐式行为（魔法常量、吞异常、无边界重试、隐藏的全局状态）。
- **改完要自查**：每次修改后都应回看 diff，确保改动与意图一致、无泄漏敏感信息、无无关文件被改动。
- **AI 工作总结**：
  - 生成代码中要在其注释中总结你的关键中间步骤，如 app/core/voice/tts_api.py 记录了你如何从官方文档页面收集数据并处理
- **Git 工作流**：
  - 每完成一次改动，生成一句话总结、详细描述
 
### 工程文档维护

- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md` 指南、及其他 markdown 文件，请同步更新该目录下的 `AGENTS.md`、及其他 markdown 文件。
- 你应该维护的 Markdown 文件应从以下文件中选择：`README.md`、`TODOS.md`、`AGENTS.md`
- Markdown 文件命名：全部使用 `.md` 后缀（小写），文件名使用全大写字母与下划线，例如 `FUTURE_PLANS.md`。
- 修改后务必回看 diff，确认无误再提交/交付。
- 测试步骤写入 tests/docs/ 如 tests/docs/TEST_STEPS_RUNTIME_URL_SWITCH.md
- 新功能/需求开发对应的文档应该添加 FR_ 前缀，如 docs/FR_CHAR_BOOSTING.md

### README.md AGENTS.md 内容


```text:https://app.monosketch.io/?id=02-AA-p-YYNmJ9TDuzP6YdRCnaWois
                 Human developers、human product          
README.md        designer etc                            
                                                         
    △            ────────────────────────────────────────
    │                                                    
    │                                                    
    │                                                    
    │ Higher                                             
    │ abstraction────────────────────────────────────────
    │ Higher                                             
    │ intuitivity                                        
    │                                                    
    │                                                    
    │            ────────────────────────────────────────
                                                         
AGENTS.md        AI                                      
                                                         
```

## Alembic

- 按照 alembic/README.md 中的步骤创建新的 alembic version 文件，而不是直接编写
- 修改数据库表 schema 应该**单独**进行，不要与其他改动混合：保证 alembic version 可以快速同步，避免多人并行产生非线性迁移链。
  - 例如：当前 alembic head revision 为 1，改动 A 与改动 B 同时修改 DB，则可能出现两个并行 version 文件都依赖 revision 1。

## Python-Kotlin HTTP APIs 数据类型定义

下面 2 处代码需要同步修改：

- [Kotlin API 数据类型](android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model)
- [Python HTTP API 数据类型](app/schemas)

## Python

- 避免使用 `try ... except Exception` 覆盖所有异常；只捕获当前函数**能够处理**的特定异常类型。
- 测试用例目录不应被声明为包：包含 `test_*.py` 的测试目录不要放置 `__init__.py`；但用于复用的测试辅助库目录应当作为包存在，并包含 `__init__.py`。
- 所有正式 Python 包必须包含空的 `__init__.py`（仅用于声明包）
- 严禁向已有的 `__init__.py` 内添加新逻辑代码（除非该目录规则明确要求）
- 使用 [cyclopts](https://github.com/BrianPugh/cyclopts) 来实现命令行界面
- 禁止使用 `__main__.py` 这种范式，使用显式的 `main.py` 入口文件

## Android App

- Android 发布新版本后将 version code 写入 [Prod 后端配置文件](devops/config.yaml.prod) `google_play.current_version_code`

## CloudFlare CDN（用于支持媒体文件分发：image audio 等）

- @<https://developers.cloudflare.com/llms.txt>
- @<https://developers.cloudflare.com/workers/prompt.txt>
- @<https://developers.cloudflare.com/stream/llms-full.txt>
- @<https://developers.cloudflare.com/developer-platform/llms-full.txt>

来自官方文档链接 https://developers.cloudflare.com/stream/changelog/
