#!/usr/bin/env bash
# 从后端日志文件中提取「生图失败 - 完整提示词」后的场景可视化提示词文本（即 "You are a scene visualization expert..." 起至下一条日志行之前）。
# 用法:
#   ssh inty 'docker logs inty-backend-prod &>prod_logs.txt'
#   scp inty:prod_logs.txt tmp/
#   ./scripts/extract_scene_prompts_from_logs.sh [--out-dir DIR] tmp/prod_logs.txt
# 若不指定 LOGFILE，默认读取 tmp/logs。

set -euo pipefail

OUT_DIR=""
LOG_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    *)
      if [[ -z "$LOG_FILE" ]]; then
        LOG_FILE="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        exit 1
      fi
      ;;
  esac
done

: "${LOG_FILE:=tmp/logs}"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "Log file not found: $LOG_FILE" >&2
  exit 1
fi

if [[ -n "$OUT_DIR" ]]; then
  mkdir -p "$OUT_DIR"
fi

# 提取逻辑：遇到「生图失败 - 完整提示词」后的下一行开始为提示词；直到遇到以 YYYY-MM-DD 开头的日志行结束。
# 使用 awk 按行处理，输出纯提示词内容（不含日志行）。
awk -v out_dir="$OUT_DIR" '
BEGIN {
  in_block = 0
  block_num = 0
  first_line_of_block = 0
}

# 当前行是「完整提示词」的日志行：下一行开始是提示词
/生图失败 - 完整提示词/ {
  in_block = 1
  block_num++
  first_line_of_block = 1
  if (out_dir == "")
    print "========== Block " block_num " =========="
  next
}

# 已进入提示词块
in_block {
  # 遇到下一条日志行（以日期开头）：结束当前块，并可能开始新块（由上面规则处理）
  if ($0 ~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}/) {
    in_block = 0
    next
  }
  # 首行跳过“空行”（紧跟日志后的换行），若需要保留空行可删掉下面两行
  if (first_line_of_block && $0 == "") {
    first_line_of_block = 0
    next
  }
  first_line_of_block = 0

  if (out_dir != "") {
    # 写入单独文件
    fname = out_dir "/scene_prompt_" sprintf("%05d", block_num) ".txt"
    print $0 >> fname
    close(fname)
  } else {
    print $0
  }
  next
}

# 每输出完一个块（stdout 模式）在块末打印空行以便阅读
END {
  if (out_dir == "" && block_num > 0)
    print ""
}
' "$LOG_FILE"

# stdout 模式下在最后加一条分隔，便于区分“下一段内容”
if [[ -z "$OUT_DIR" ]] && [[ -f "$LOG_FILE" ]]; then
  count=$(grep -c "生图失败 - 完整提示词" "$LOG_FILE" || true)
  if [[ "${count:-0}" -gt 0 ]]; then
    echo "========== End of extraction ($count blocks) =========="
  fi
fi
