# 入口：在仓库根目录执行 python -m experimental.agentic_ai_companion.main 启动最小化 role play。
# CREATED_BY_AGENT

import cyclopts

from .chat import main

if __name__ == "__main__":
    cyclopts.run(main)
