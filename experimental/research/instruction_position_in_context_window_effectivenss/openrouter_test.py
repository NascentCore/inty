#!/usr/bin/env python3
"""
OpenRouter Long Context Performance Test

This script tests the performance of various LLM models via OpenRouter with long context input (~500k tokens).
It measures:
- First token latency (time to receive the first token)
- Total response time
- Token processing speed

Usage:
1. Download a book text file to ./data/book.txt
2. Set your OpenRouter API key in environment variable OPENROUTER_API_KEY
3. Run: python openrouter_test.py --model claude-3.5-sonnet
"""

import argparse
import asyncio
import os
import random
import time
from pathlib import Path
from typing import Optional

import tiktoken
from openai import AsyncOpenAI


class PerformanceTracker:
    """Simple performance tracking for OpenRouter API calls."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.first_token_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.token_count: int = 0
        self.response_tokens: int = 0

    def start(self):
        """Start timing."""
        self.start_time = time.perf_counter()

    def mark_first_token(self):
        """Mark when first token is received."""
        if self.first_token_time is None:
            self.first_token_time = time.perf_counter()

    def end(self):
        """End timing."""
        self.end_time = time.perf_counter()

    def get_metrics(self) -> dict:
        """Get performance metrics in milliseconds."""
        if not all([self.start_time, self.first_token_time, self.end_time]):
            return {}

        first_token_latency = (self.first_token_time - self.start_time) * 1000
        total_time = (self.end_time - self.start_time) * 1000

        metrics = {
            "first_token_latency_ms": round(first_token_latency, 2),
            "total_response_time_ms": round(total_time, 2),
            "input_tokens": self.token_count,
            "response_tokens": self.response_tokens,
        }

        if total_time > 0:
            metrics["tokens_per_second"] = round(
                self.response_tokens / (total_time / 1000), 2
            )

        return metrics


def load_book_text(file_path: str) -> str:
    """Load book text from file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Book file not found: {file_path}\n"
            "Please download a book text file to ./data/book.txt\n"
            "Recommended: Pride and Prejudice from Project Gutenberg"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Loaded book: {len(content)} characters")
        return content
    except Exception as e:
        raise Exception(f"Error reading book file: {e}")


async def test_openrouter_performance_with_retry(
    book_text: str, model: str, question: str = None, max_retries: int = 3
) -> dict:
    """Test OpenRouter performance with long context and retry mechanism."""

    for attempt in range(max_retries):
        try:
            return await test_openrouter_performance(book_text, model, question)
        except Exception as e:
            error_str = str(e).lower()
            if any(
                keyword in error_str
                for keyword in [
                    "connection reset by peer",
                    "timeout",
                    "server disconnected",
                    "connection aborted",
                    "connection lost",
                    "rate limit",
                ]
            ):
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    print(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue
            raise e


async def test_openrouter_performance(
    book_text: str, model: str, question: str = None
) -> dict:
    """Test OpenRouter model performance with long context."""

    # Default question if none provided
    if not question:
        question = "Please provide a brief summary of this book in 3-4 sentences."

    # Initialize OpenAI client with OpenRouter endpoint
    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    except Exception as e:
        raise Exception(
            f"Failed to initialize OpenRouter client: {e}\nMake sure OPENROUTER_API_KEY is set"
        )

    # Prepare the full prompt
    full_prompt = f"""Here is the complete text of a book:

{book_text}

---

Question: {question}"""

    # Count tokens
    token_count = safe_count_tokens(full_prompt, "input")
    print(f"Input tokens: ~{token_count:,}")

    # Performance tracker
    tracker = PerformanceTracker()
    tracker.token_count = token_count

    tracker.start()

    try:
        # Generate content with streaming to capture first token
        stream = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.1,
            max_tokens=2048,
            stream=True,
        )

        response_text = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                # Mark first token on first chunk with content
                if not response_text:
                    tracker.mark_first_token()

                response_text += chunk.choices[0].delta.content

        # Count response tokens
        tracker.response_tokens = safe_count_tokens(response_text, "response")
        tracker.end()

        print(f"\nResponse received:")
        print("-" * 50)
        print(response_text)
        print("-" * 50)

        return tracker.get_metrics()

    except Exception as e:
        tracker.end()
        raise Exception(f"Error calling OpenRouter API: {e}")


def safe_count_tokens(text: str, context: str = "") -> int:
    """Safely count tokens with better error handling."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimation (1 token ≈ 4 characters for English text)
        estimated = len(text) // 4
        if context:
            print(f"Using fallback token estimation for {context}: ~{estimated:,}")
        return estimated


def get_model_pricing(model: str) -> tuple[float, float]:
    """Get approximate pricing for different models (per 1M tokens)."""
    pricing_map = {
        # Claude models
        "claude-3.5-sonnet": (3.0, 15.0),
        "claude-3-sonnet": (3.0, 15.0),
        "claude-3-haiku": (0.25, 1.25),
        "claude-3-opus": (15.0, 75.0),
        # GPT models
        "gpt-4o": (2.5, 10.0),
        "gpt-4-turbo": (10.0, 30.0),
        "gpt-4": (30.0, 60.0),
        "gpt-3.5-turbo": (0.5, 1.5),
        # Other models
        "mistral-large": (2.0, 6.0),
        "llama-3.1-405b": (2.7, 2.7),
        "llama-3.1-70b": (0.59, 0.79),
    }

    # Default pricing if model not found
    return pricing_map.get(model, (1.0, 3.0))


def print_results(metrics: dict, model: str):
    """Print performance results in a nice format."""
    print("\n" + "=" * 70)
    print("OPENROUTER LONG CONTEXT PERFORMANCE RESULTS")
    print("=" * 70)
    print(f"Model:                  {model}")
    print(f"Input tokens:           {metrics.get('input_tokens', 0):,}")
    print(f"Output tokens:          {metrics.get('response_tokens', 0):,}")
    print(
        f"Total tokens:           {metrics.get('input_tokens', 0) + metrics.get('response_tokens', 0):,}"
    )
    print(f"First token latency:    {metrics.get('first_token_latency_ms', 0):.2f} ms")
    print(f"Total response time:    {metrics.get('total_response_time_ms', 0):.2f} ms")
    print(
        f"Processing speed:       {metrics.get('tokens_per_second', 0):.2f} tokens/sec"
    )

    # Calculate cost estimate
    input_tokens = metrics.get("input_tokens", 0)
    output_tokens = metrics.get("response_tokens", 0)
    input_price, output_price = get_model_pricing(model)

    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price
    total_cost = input_cost + output_cost
    print(f"Estimated cost:         ${total_cost:.4f} USD")
    print(f"  - Input cost:         ${input_cost:.4f} USD")
    print(f"  - Output cost:        ${output_cost:.4f} USD")
    print("=" * 70)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test OpenRouter model performance with long context input",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python openrouter_test.py --model claude-3.5-sonnet --book-path ./data/moby-dick.txt
  python openrouter_test.py --model gpt-4o  # uses default ./data/book.txt

Popular models:
  - claude-3.5-sonnet: Latest Claude model with excellent performance
  - claude-3-haiku: Fast and cost-effective Claude model  
  - gpt-4o: Latest GPT-4 model with good performance
  - gpt-3.5-turbo: Cost-effective option
  - mistral-large: Competitive alternative
  - llama-3.1-405b: Large open-source model

Recommended books by token count:
  - Alice in Wonderland: ~27k tokens (light test)
  - The Great Gatsby: ~50k tokens (medium test)  
  - Moby Dick: ~200k tokens (large test)
  - The Count of Monte Cristo: ~460k tokens (very large test)

Download from Project Gutenberg: https://www.gutenberg.org/
        """,
    )

    parser.add_argument(
        "--model",
        type=str,
        default="claude-3.5-sonnet",
        help="Model to test (default: claude-3.5-sonnet)",
    )

    parser.add_argument(
        "--book-path",
        type=str,
        default="./data/book.txt",
        help="Path to the book text file (default: ./data/book.txt)",
    )

    parser.add_argument(
        "--question",
        type=str,
        help="Custom question to ask about the book (optional)",
    )

    return parser.parse_args()


async def main():
    """Main test function."""

    # Parse command line arguments
    args = parse_arguments()

    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY environment variable not set")
        print("Please set your OpenRouter API key:")
        print("export OPENROUTER_API_KEY='your-api-key-here'")
        print("\nGet your API key from: https://openrouter.ai/keys")
        return

    # Load book text
    try:
        book_text = load_book_text(args.book_path)
    except Exception as e:
        print(f"ERROR: {e}")
        return

    # Run the test
    try:
        print(f"Starting OpenRouter long context performance test...")
        print(f"Model: {args.model}")
        print(f"Book file: {args.book_path}")

        # Test performance with retry
        first_question = (
            args.question
            or "Please provide a brief summary of this book in 3-4 sentences."
        )
        metrics = await test_openrouter_performance_with_retry(
            book_text, args.model, first_question
        )
        print_results(metrics, args.model)

    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
