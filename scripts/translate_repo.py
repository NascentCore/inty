#！/usr/bin/env python3
import asyncio
import concurrent.futures
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import yaml
import urllib.parse
import urllib.request
# 简洁日志
def log_debug(msg: str) -> None:
    print(msg)

@dataclass
class Config:
    provider: str
    model: str
    mode: str
    concurrency: int
    max_chars_per_chunk: int
    protected_terms: List[str]
    include_extensions: List[str]
    exclude_dirs: List[str]
    process_markdown: bool
    process_comments: bool
    process_docstrings: bool

    @staticmethod
    def load(path: Path) -> "Config":
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return Config(
            provider=data.get("provider", "openai"),
            model=data.get("model", "gpt-4o-mini"),
            mode=data.get("mode", "dry-run"),
            concurrency=int(data.get("concurrency", 2)),
            max_chars_per_chunk=int(data.get("max_chars_per_chunk", 3500)),
            protected_terms=list(data.get("protected_terms", [])),
            include_extensions=list(data.get("include_extensions", [".md"])),
            exclude_dirs=list(data.get("exclude_dirs", [])),
            process_markdown=bool(data.get("process_markdown", True)),
            process_comments=bool(data.get("process_comments", True)),
            process_docstrings=bool(data.get("process_docstrings", False)),
        )
#文件翻译
EXCLUDE_DEFAULT = {
    ".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__"
}

COMMENT_PATTERNS = {
    ".py": re.compile(r"(^\s*#.*$)", re.MULTILINE),
    ".ts": re.compile(r"(^\s*\/\/.*$)|(/\*[\s\S]*?\*/)", re.MULTILINE),
    ".tsx": re.compile(r"(^\s*\/\/.*$)|(/\*[\s\S]*?\*/)", re.MULTILINE),
    ".js": re.compile(r"(^\s*\/\/.*$)|(/\*[\s\S]*?\*/)", re.MULTILINE),
    ".jsx": re.compile(r"(^\s*\/\/.*$)|(/\*[\s\S]*?\*/)", re.MULTILINE),
    ".kt": re.compile(r"(^\s*\/\/.*$)|(/\*[\s\S]*?\*/)", re.MULTILINE),
    ".kts": re.compile(r"(^\s*\/\/.*$)|(/\*[\s\S]*?\*/)", re.MULTILINE),
    ".sh": re.compile(r"(^\s*#.*$)", re.MULTILINE),
    ".xml": re.compile(r"(<!--[\s\S]*?-->)", re.MULTILINE),
    ".html": re.compile(r"(<!--[\s\S]*?-->)", re.MULTILINE),
}

MD_CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)
MD_HTML_COMMENT = re.compile(r"(<!--[\s\S]*?-->)", re.MULTILINE)
INLINE_CODE = re.compile(r"`[^`\n]+`")
URL_PATTERN = re.compile(r"https?://[^\s)\]>]+")

def iter_files(root: Path, cfg: Config) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
# 排除目录
        skip = False
        for pattern in list(EXCLUDE_DEFAULT) + cfg.exclude_dirs:
            if pattern and (rel_dir == pattern or rel_dir.startswith(pattern + os.sep)):
                skip = True
                break
        if skip:
            dirnames[:] = []
            continue
        for name in filenames:
            ext = os.path.splitext(name)[1]
            if ext in cfg.include_extensions:
                yield Path(dirpath) / name
# 保护词占位
PLACEHOLDER_PREFIX = "__KEEP__"

def mask_protected_terms(text: str, terms: List[str]) -> Tuple[str, List[str]]:
    placeholders: List[str] = []
    def repl(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"{PLACEHOLDER_PREFIX}{len(placeholders)-1}__"
    for term in sorted(terms, key=len, reverse=True):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(repl, text)
    return text, placeholders

def unmask_placeholders(text: str, placeholders: List[str]) -> str:
    for idx, original in enumerate(placeholders):
        text = text.replace(f"{PLACEHOLDER_PREFIX}{idx}__", original)
    return text

def mask_urls(text: str) -> Tuple[str, List[str]]:
    urls: List[str] = []
    def repl(m: re.Match[str]) -> str:
        urls.append(m.group(0))
        return f"__URLKEEP_{len(urls)-1}__"
    return URL_PATTERN.sub(repl, text), urls

def unmask_urls(text: str, urls: List[str]) -> str:
    for i, u in enumerate(urls):
        text = text.replace(f"__URLKEEP_{i}__", u)
    return text
# LLM 翻译
async def translate_text_openai(model: str, text: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    sys_prompt = (
        "你是专业技术译者。将输入英文翻成简体中文；保持极简风格，只保留核心信息；"
        "专有名词与技术词汇（如 API/SDK/FastAPI/React/inty 等）保持英文不变；"
        "不要添加解释，不要润色，不要改变列表/缩进/代码片段结构。"
    )
    resp = await client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content or ""

def google_translate_http(text: str, target_lang: str = "zh-CN") -> str:
# 使用非官方公开烟草；按剂量避免 URL 过长
    if not text:
        return ""
    max_len = 700
    parts: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
#尝试在句号/换行处分割
        slice_text = text[start:end]
        back = slice_text.rfind("\n")
        if back < int(max_len * 0.6):
            back = max(slice_text.rfind("."), slice_text.rfind("!"), slice_text.rfind("?"))
        if back > 0:
            end = start + back + 1
            slice_text = text[start:end]
        q = urllib.parse.quote(slice_text)
        url = (
            "https://translate.googleapis.com/translate_a/single?client=gtx"
            f"&sl=en&tl={urllib.parse.quote(target_lang)}&dt=t&q={q}"
        )
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = resp.read().decode("utf-8")
        try:
            obj = json.loads(data)
            out = "".join(seg[0] for seg in obj[0])
        except Exception:
            out = slice_text
        parts.append(out)
        start = end
    return "".join(parts)

async def translate_chunks(cfg: Config, chunks: List[str]) -> List[str]:
    if cfg.mode == "dry-run":
        return chunks
    results: List[str] = [""] * len(chunks)
    sem = asyncio.Semaphore(cfg.concurrency)

    async def worker(i: int, content: str) -> None:
        async with sem:
            try:
                if cfg.provider == "openai":
                    out = await translate_text_openai(cfg.model, content)
                else:
                    out = await asyncio.to_thread(google_translate_http, content, "zh-CN")
            except Exception as e:
# 无可用模型或网络错误时，保留版本
                log_debug(f"翻译失败，保留原文 idx={i}: {e}")
                out = content
            results[i] = out

    await asyncio.gather(*(worker(i, ch) for i, ch in enumerate(chunks)))
    return results
# Markdown 翻译：忽略代码块，仅翻正文与 HTML 注释
def translate_markdown_text(cfg: Config, text: str) -> Tuple[str, List[Tuple[int, int, str, str]]]:
    url_masked, urls = mask_urls(text)
    protected_text, placeholders = mask_protected_terms(url_masked, cfg.protected_terms)
    segments: List[Tuple[int, int]] = []
    last = 0
    for m in MD_CODE_BLOCK.finditer(protected_text):
        if m.start() > last:
            segments.append((last, m.start()))
        last = m.end()
    if last < len(protected_text):
        segments.append((last, len(protected_text)))
# 在非代码块段内，进一步切分：HTML 注释与行内代码
    final_spans: List[Tuple[int, int, str]] = []  # (start, end, kind)
    for s, e in segments:
        seg = protected_text[s:e]
# 先按 HTML 注释切分
        temp_spans: List[Tuple[int, int, str]] = []
        last2 = 0
        for c in MD_HTML_COMMENT.finditer(seg):
            if c.start() > last2:
                temp_spans.append((s + last2, s + c.start(), "text"))
            temp_spans.append((s + c.start(), s + c.end(), "comment"))
            last2 = c.end()
        if last2 < len(seg):
            temp_spans.append((s + last2, e, "text"))
# 在每个文本段内再切分出行内代码
        for ts, te, kind in temp_spans:
            if kind != "text":
                final_spans.append((ts, te, kind))
                continue
            inner = protected_text[ts:te]
            last3 = 0
            for ic in INLINE_CODE.finditer(inner):
                if ic.start() > last3:
                    final_spans.append((ts + last3, ts + ic.start(), "text"))
                final_spans.append((ts + ic.start(), ts + ic.end(), "code"))
                last3 = ic.end()
            if last3 < len(inner):
                final_spans.append((ts + last3, te, "text"))

    tasks: List[str] = []
    kinds: List[str] = []
    for s, e, k in final_spans:
        piece = protected_text[s:e]
        tasks.append(piece)
        kinds.append(k)
# 分块
    merged_tasks: List[str] = []
    idx_map: List[List[int]] = []
    buf: List[str] = []
    acc = 0
    cur_idx: List[int] = []
    for i, t in enumerate(tasks):
        if acc + len(t) > cfg.max_chars_per_chunk and buf:
            merged_tasks.append("".join(buf))
            idx_map.append(cur_idx)
            buf, cur_idx, acc = [], [], 0
        buf.append(t)
        cur_idx.append(i)
        acc += len(t)
    if buf:
        merged_tasks.append("".join(buf))
        idx_map.append(cur_idx)
# 直接翻译可翻部分（text/comment），代码段原样保留
    def needs_translation(s: str) -> bool:
#含有足量英文字母时才翻译
        letters = sum(1 for ch in s if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
        if letters < 5:
            return False
        ratio = letters / max(1, len(s))
        return ratio >= 0.1

    to_translate_indices = [
        i for i, k in enumerate(kinds)
        if k in ("text", "comment") and needs_translation(tasks[i])
    ]
    to_translate_chunks = [tasks[i] for i in to_translate_indices]
    if cfg.mode == "dry-run":
        translated_chunks = to_translate_chunks
    else:
        translated_chunks = asyncio.run(translate_chunks(cfg, to_translate_chunks))

    translated_tasks: List[str] = [""] * len(tasks)
    it = iter(translated_chunks)
    for i, k in enumerate(kinds):
        if k in ("text", "comment") and needs_translation(tasks[i]):
            translated_tasks[i] = next(it)
        else:
            translated_tasks[i] = tasks[i]
# 一起
    out_chars = list(protected_text)
    cursor = 0
    result_parts: List[str] = []
    for i, (s, e, _k) in enumerate(final_spans):
        if s > cursor:
            result_parts.append(protected_text[cursor:s])
        piece_translated = translated_tasks[i]
        result_parts.append(piece_translated)
        cursor = e
    if cursor < len(protected_text):
        result_parts.append(protected_text[cursor:])

    result = "".join(result_parts)
    result = unmask_placeholders(result, placeholders)
    result = unmask_urls(result, urls)
#构造变更列表（用于报告）
    changes_report: List[Tuple[int, int, str, str]] = []
    for i, (s, e, _k) in enumerate(final_spans):
        changes_report.append((s, e, tasks[i], translated_tasks[i]))
    return result, changes_report
# 注释 翻译
def translate_comments_in_code(cfg: Config, text: str, ext: str) -> Tuple[str, List[Tuple[int, int, str, str]]]:
    pattern = COMMENT_PATTERNS.get(ext)
    if not pattern:
        return text, []
    url_masked, urls = mask_urls(text)
    protected_text, placeholders = mask_protected_terms(url_masked, cfg.protected_terms)
    changes: List[Tuple[int, int, str, str]] = []

    def repl(m: re.Match[str]) -> str:
        orig = m.group(0)
        if cfg.mode == "dry-run":
            changes.append((m.start(), m.end(), orig, orig))
            return orig
# 同步调用子协程：单条调用可能采用阻塞，长度截断值拆分
        chunks: List[str] = []
        start = 0
        while start < len(orig):
            end = min(start + cfg.max_chars_per_chunk, len(orig))
            chunks.append(orig[start:end])
            start = end
        outs = asyncio.run(translate_chunks(cfg, chunks))
        out = "".join(outs)
        changes.append((m.start(), m.end(), orig, out))
        return out

    new_text = pattern.sub(repl, protected_text)
    new_text = unmask_placeholders(new_text, placeholders)
    new_text = unmask_urls(new_text, urls)
    return new_text, changes

def process_file(path: Path, cfg: Config) -> Optional[dict]:
    ext = path.suffix
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        log_debug(f"跳过不可读文件: {path}: {e}")
        return None

    if ext == ".md" and cfg.process_markdown:
        new_text, changes = translate_markdown_text(cfg, content)
    elif cfg.process_comments and ext in COMMENT_PATTERNS:
        new_text, changes = translate_comments_in_code(cfg, content, ext)
    else:
        return None

    if cfg.mode == "write" and new_text != content:
        path.write_text(new_text, encoding="utf-8")

    return {
        "file": str(path),
        "changed": new_text != content,
        "changes": [
            {"start": s, "end": e, "before": b, "after": a}
            for (s, e, b, a) in changes
        ],
    }

async def run(cfg: Config, root: Path) -> List[dict]:
    files = list(iter_files(root, cfg))
    results: List[dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, cfg.concurrency * 2)) as pool:
        loop = asyncio.get_running_loop()
        tasks = [loop.run_in_executor(pool, process_file, f, cfg) for f in files]
        for fut in asyncio.as_completed(tasks):
            item = await fut
            if item:
                results.append(item)
    return results

def main() -> None:
    root = Path(os.getenv("WORKSPACE", ".")).resolve()
    cfg_path = Path("scripts/translate_config.yaml")
    cfg = Config.load(cfg_path)
    log_debug("开始扫描与翻译（可能为 dry-run）...")
    results = asyncio.run(run(cfg, root))
    report_path = Path("scripts/translate_report.json")
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    changed = sum(1 for r in results if r.get("changed"))
    total = len(results)
    log_debug(f"处理文件 {total} 个，变化 {changed} 个。报告: {report_path}")

if __name__ == "__main__":
    main()
