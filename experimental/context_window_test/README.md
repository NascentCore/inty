# Gemini 2.5 Pro Long Context Performance Test

This tool tests Gemini 2.5 Pro performance with long context input (~500k tokens), measuring first token latency and total response time.

## Quick Start

### 1. Download Test Data

Choose a book based on your testing needs:

**Light Testing (~50k tokens)**:
```bash
# Alice's Adventures in Wonderland (~27k tokens)
curl -o data/book.txt https://www.gutenberg.org/files/11/11-0.txt

# The Great Gatsby (~50k tokens) 
curl -o data/book.txt https://www.gutenberg.org/files/64317/64317-0.txt
```

**Medium Testing (~200k tokens)**:
```bash
# Moby Dick (~200k tokens)
curl -o data/book.txt https://www.gutenberg.org/files/2701/2701-0.txt
```

**Heavy Testing (400k+ tokens)**:
```bash
# The Count of Monte Cristo (~460k tokens)
curl -o data/book.txt https://www.gutenberg.org/files/1184/1184-0.txt

# War and Peace (~600k tokens) - may cause timeout
curl -o data/book.txt https://www.gutenberg.org/files/2600/2600-0.txt
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set API Key

```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```

### 4. Run Test

```bash
# Use default book (./data/book.txt)
python context_test.py

# Specify custom book path
python context_test.py --book-path ./data/moby-dick.txt

# Use custom question
python context_test.py --book-path ./data/alice.txt --question "What are the main themes in this story?"

# Show help
python context_test.py --help
```

## Output Example

```
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
```

## What It Measures

- **First Token Latency**: Time from request to first response token
- **Total Response Time**: Complete request-response cycle
- **Token Processing Speed**: Response tokens per second
- **Token Counts**: Input and output token counts

## Book Recommendations by Token Count

**🟢 Light (Start Here)**:
- **Alice's Adventures in Wonderland** (~27k tokens) - Quick test
- **The Great Gatsby** (~50k tokens) - Modern classic

**🟡 Medium**:  
- **Moby Dick** (~200k tokens) - Classic literature
- **Pride and Prejudice** (~180k tokens) - Jane Austen

**🔴 Heavy (May Timeout)**:
- **The Count of Monte Cristo** (~460k tokens) - Adventure epic
- **War and Peace** (~600k tokens) - Russian masterpiece

**💡 Recommendation**: Start with Alice in Wonderland or Moby Dick to avoid timeout issues.

Download from [Project Gutenberg](https://www.gutenberg.org/).

## Requirements

- Python 3.8+
- Google API key with Gemini access
- ~1MB free disk space for book text

## Notes

- Uses `gemini-2.0-flash-exp` model (supports long context)
- Token counting is approximate (using tiktoken)
- Results may vary based on network and API load