# Python 代码异味报告

下列为在本仓库中检出的具有代表性的 Python code smell（含文件与片段举例）与改进建议。仅列出最重要、最具风险或最广泛分布的模式。

## 1. 宽泛/裸异常捕获（except Exception/except:）
- 现象：大量 `except Exception as e:` 与若干 `except:`（裸异常）
- 代表位置：
  - `app/external_services/google_play_service.py` 多处 `except Exception as e:`（示例：L65, L110, L140, L170, ...）
  - `app/services/character_card_service.py`（L128, L192, L283, L303, L332, L379）
  - `app/services/chat_service.py`、`app/api/*/endpoints/*.py`、`app/services/*` 广泛存在
  - 裸异常：`app/services/character_card_service.py:369`、`experimental/civitai/*.py`、`app/services/scoring_service.py:241`
- 风险：吞掉关键异常、掩盖编程错误、难以定位问题；也可能误处理系统级异常。
- 建议：
  - 捕获更具体的异常类型；
  - 记录上下文并在必要时重抛；
  - 对不可恢复错误返回显式错误码或让上层处理。

## 2. 空异常处理与忽略错误（except ...: pass）
- 代表位置：
  - `app/services/chat_service.py:760-762`、`app/services/evaluation_service.py:635-637`
  - `app/services/subscription_service.py:741-742`、`app/services/voice_cache_service.py:*`（事务回滚失败被忽略）
  - `experimental/*` 多处
- 风险：静默失败导致数据不一致、难以排查。
- 建议：至少 `logger.warning/error` 记录错误与上下文；对于必须忽略的情况写出明确注释与理由。

## 3. 标准输出打印用于日志/配置
- 代表位置：
  - `app/core/config.py` 在导入阶段 `print("[CONFIG] ...")` 与 `print("Database URL ...")`
  - `app/utils/timing.py` 文档字符串示例使用 `print`（且拼写 `mesage`）
  - `app/core/agent/agent.py:1009,1012`、`app/utils/crop_avatar.py` 多处 `print`
- 风险：与日志体系不一致、产线噪音、泄露敏感信息（如数据库URL）。
- 建议：用 `loguru.logger`；避免模块 import 时打印；敏感信息脱敏。

## 4. 使用 `assert` 于运行时代码路径（而非仅测试）
- 代表位置：
  - `app/external_services/gcs.py:108-116`、`:190-205` 用 `assert` 校验输入
- 风险：`python -O` 可移除断言导致校验失效；断言异常类型不适合 API 层。
- 建议：改为显式条件判断并抛出 `ValueError`/`RuntimeError` 等；或返回结构化错误。

## 5. 可执行阻塞等待 `time.sleep`（非测试）
- 代表位置：
  - `app/utils/timing.py:35` 示例代码 `time.sleep(0.1)`（可能仅示例）
- 风险：若误入生产路径会阻塞；
- 建议：确保仅用于测试/示例；生产路径使用异步或重试策略。

## 6. 违背 PEP8/可读性问题的小异味
- 代表位置与问题：
  - `app/api/v1/endpoints/auth.py:79,129` 使用 `== None` 判断，建议 `is None`
  - `app/utils/timing.py` 注释/文案中 `Timeer`、`mesage` 拼写错误
- 风险：可读性下降、易误导。
- 建议：统一风格与拼写；使用 linter/formatter 守护。

## 7. 使用 eval
- 代表位置：
  - `experimental/agent_tags_migration/tag_parser.py:160` 执行 `eval(json_str, {"__builtins__": {}}, {})`
- 风险：安全风险（即便禁用 builtins 仍可能有逃逸风险）。
- 建议：严格改用 `json.loads` 或专用解析器。

## 8. TODO/FIXME/HACK 长期遗留
- 代表位置：`app/services/agent_service.py`、`app/api/*`、`app/models/*`、`app/core/*`、`tools/scripts/*` 等多处
- 风险：低优先级债务堆积。
- 建议：
  - 标注负责人与截止日期；
  - 对无计划事项做决断：落实或删除；
  - 重要改动转为 issue/任务流。

## 9. GCS 客户端与全局状态
- 代表位置：`app/external_services/gcs.py` 顶层初始化 `gcs_client`
- 风险：导入即副作用、测试不易、凭据读取时序耦合。
- 建议：延迟初始化/注入式创建；提供健康检查与失败回退。

## 10. 统一日志语义与等级
- 现象：`logger.error`/`warning`/`info` 等等级混用；部分异常路径返回 `{"error": str(e)}`。
- 建议：定义错误分级与返回规范；为用户态错误返回可读提示，为系统态错误保留内部日志与追踪ID。

---

### 建议的工程治理措施
- 启用并收紧 linter 规则（flake8/ruff + mypy + black/ruff format）；
- 在 CI 中新增 “禁止裸/宽泛异常” 规则白名单机制；
- 引入统一错误模型与异常基类；
- 逐步移除 `print`；
- 为 `experimental/` 目录加上“非生产”检查或分离到独立包。
