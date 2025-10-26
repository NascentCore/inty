# Gemini 2.5 Pro 长上下文性能测试

该工具使用长上下输入（~500k 令牌）测试 Gemini 2.5 Pro 性能，测量第一个令牌延迟和总响应时间。

## 快速入门

### 1.下载测试数据

根据您的测试需求选择一本书：

** 挪威测试（~50k 代币）**：```bash
# Alice's Adventures in Wonderland (~27k tokens)
curl -o data/book.txt https://www.gutenberg.org/files/11/11-0.txt

# The Great Gatsby (~50k tokens)
curl -o data/book.txt https://www.gutenberg.org/files/64317/64317-0.txt
```**中等测试（~200k 代币）**：```bash
# Moby Dick (~200k tokens)
curl -o data/book.txt https://www.gutenberg.org/files/2701/2701-0.txt
```**大量测试（400k+ 代币）**：```bash
# The Count of Monte Cristo (~460k tokens)
curl -o data/book.txt https://www.gutenberg.org/files/1184/1184-0.txt

# War and Peace (~600k tokens) - may cause timeout
curl -o data/book.txt https://www.gutenberg.org/files/2600/2600-0.txt
```### 2.安装依赖项```bash
pip install -r requirements.txt
```### 3.设置 API 密钥```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```### 4.运行测试```bash
# Use default book (./data/book.txt)
python context_test.py

# Specify custom book path
python context_test.py --book-path ./data/moby-dick.txt

# Use custom question
python context_test.py --book-path ./data/alice.txt --question "What are the main themes in this story?"

# Show help
python context_test.py --help
```## 输出示例```
Loaded book: 717569 characters
Input tokens: ~179,392
Sending request to Gemini 2.5 Pro...

Response received:
--------------------------------------------------
Pride and Prejudice follows Elizabeth Bennet, a witty young woman...
--------------------------------------------------

============================================================
GEMINI 2.5 PRO LONG CONTEXT PERFORMANCE RESULTS
============================================================
Input tokens:           179,392
Response tokens:        156
First token latency:    2,450.23 ms
Total response time:    3,120.45 ms
Processing speed:       49.98 tokens/sec
============================================================
```## 它测量什么

- **第一个令牌延迟**：从请求到第一个响应令牌的时间
- **总响应时间**：完整的请求-响应周期
- **令牌Processing速度**：每秒请求令牌数
- **令牌计数**：输入和输出令牌计数

## 按代币数量推荐书籍

**🟢光（从这里开始）**：

- **爱丽丝梦游仙境** (~27k 代币) - 快速测试
- **了不起的盖茨比**（~5万代币）- 现代经典

**🟡平均**：

- **白鲸记**（~20万代币）- 经典文学
- **Pride 和 Prejudice** （约 180k 代币）- Jane Austen

**🔴重度（可能超时）**：

- **基督山伯爵**（~460k 代币）- 冒险史诗- **战争与和平**（~600k 代币）- 俄罗斯杰作

**💡建议**：从《爱丽丝梦游仙境》或《白鲸记》开始，巴勒斯坦超时问题。

从 [Project Gutenberg](https://www.gutenberg.org/) 下载。

＃＃要求

-Python 3。8+
- 具有Gemini访问权限的Google API键
- ~1MB 可用磁盘空间用于书籍文本

## 注释- 用途`gemini-2.0-flash-exp`模型（支撑长上下文）
- 代币统计为 approximate （使用 tiktoken）
- 结果可能因网络和API负载而异