# Debug Release Android App

如何在 **release 构建** 下获取调试数据（如 Love Journal 高亮相关日志）。

## Heartbeat 调试日志 (heartbeat_debug.ndjson)

应用在写入内部 `filesDir` 的同时，会通过 MediaStore 追加到公共 **Download** 目录的 `heartbeat_debug.ndjson`，便于 release 下用 adb 拉取。

### Release 构建

1. 安装 release 包，打开 Love Journal 并触发一次高亮（例如从聊天/推送进入某条记忆），以产生日志。
2. 拉取到本地：

```bash
adb -s <device_serial> pull /sdcard/Download/heartbeat_debug.ndjson .cursor/debug.log
```

示例（单设备可省略 `-s`）：

```bash
adb -s 34181JEHN02316 pull /sdcard/Download/heartbeat_debug.ndjson .cursor/debug.log
```

### Debug 构建（可选）

内部路径也可用 `run-as` 拉取（仅 debuggable 构建）：

```bash
adb -s <device_serial> shell "run-as com.ai.intellimate cat /data/data/com.ai.intellimate/files/heartbeat_debug.ndjson" > .cursor/debug.log
```

### 常见错误

| 现象 | 原因 | 处理 |
|------|------|------|
| `adb pull ... Permission denied` | 拉的是应用私有目录 | 使用 Download 路径，或（仅 debug）用 run-as |
| `adb: unrecognized option '-s'` | `-s` 位置错误 | 写成 `adb -s <serial> pull ...`，不要 `adb pull -s ...` |
| `run-as: Package '...' is not debuggable` | 当前是 release 包 | 用上面「Release 构建」的 pull 路径即可 |

## 参考

- 详细步骤与变体见 `tests/docs/TEST_STEPS_HEARTBEAT_DEBUG_PULL.md`（若存在）。
