#!/usr/bin/env python3
"""
Gemini 2.5 Pro Long Context Performance Test

This script tests the performance of Gemini 2.5 Pro with long context input (~500k tokens).
It measures:
- First token latency (time to receive the first token)
- Total response time
- Token processing speed

Usage:
1. Download a book text file to ./data/book.txt
2. Set your Google API key in environment variable GOOGLE_API_KEY
3. Run: python context_test.py
"""

import argparse
import asyncio
import os
import random
import time
from pathlib import Path
from typing import Optional

import google.genai as genai
import tiktoken
from google.genai import types


class PerformanceTracker:
    """Simple performance tracking for Gemini API calls."""

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


async def test_gemini_context_performance_with_retry(
    book_text: str, question: str = None, max_retries: int = 3
) -> dict:
    """Test Gemini performance with long context and retry mechanism."""

    for attempt in range(max_retries):
        try:
            return await test_gemini_context_performance(book_text, question)
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
                ]
            ):
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    print(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue
            raise e


async def test_gemini_context_performance(book_text: str, question: str = None) -> dict:
    """Test Gemini 2.5 Pro performance with long context."""

    # Default question if none provided
    if not question:
        question = "Please provide a brief summary of this book in 3-4 sentences."

    # Initialize client with timeout configuration
    try:
        # Configure client with longer timeout for large context
        client = genai.Client()
    except Exception as e:
        raise Exception(
            f"Failed to initialize Gemini client: {e}\nMake sure GOOGLE_API_KEY is set"
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
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )

        # Since we're not using streaming, mark first token immediately when response starts
        tracker.mark_first_token()

        # Get the response text
        response_text = ""
        if response.candidates and response.candidates[0].content.parts:
            response_text = response.candidates[0].content.parts[0].text

        # Get actual token usage from API response
        actual_input_tokens = None
        actual_output_tokens = None

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            # Check available attributes in usage_metadata
            usage = response.usage_metadata
            print(f"Usage metadata type: {type(usage)}")
            print(
                f"Available usage attributes: {[attr for attr in dir(usage) if not attr.startswith('_')]}"
            )

            # Try different possible attribute names
            actual_input_tokens = (
                getattr(usage, "prompt_token_count", None)
                or getattr(usage, "input_tokens", None)
                or getattr(usage, "prompt_tokens", None)
            )
            actual_output_tokens = (
                getattr(usage, "candidates_token_count", None)
                or getattr(usage, "output_tokens", None)
                or getattr(usage, "candidates_tokens", None)
            )

            if actual_input_tokens and actual_output_tokens:
                print(
                    f"API Token Usage - Input: {actual_input_tokens:,}, Output: {actual_output_tokens:,}"
                )
            else:
                print(
                    f"Token counts - Input: {actual_input_tokens}, Output: {actual_output_tokens}"
                )
        else:
            print("No usage_metadata found in response")

        # Use API token counts if available, otherwise fall back to estimation
        tracker.token_count = (
            actual_input_tokens if actual_input_tokens else tracker.token_count
        )
        tracker.response_tokens = (
            actual_output_tokens
            if actual_output_tokens
            else safe_count_tokens(response_text, "response")
        )
        tracker.end()

        print(f"\nResponse received:")
        print("-" * 50)
        print(response_text)
        print("-" * 50)

        return tracker.get_metrics()

    except Exception as e:
        tracker.end()
        raise Exception(f"Error calling Gemini API: {e}")


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


def print_results(metrics: dict):
    """Print performance results in a nice format."""
    print("\n" + "=" * 70)
    print("GEMINI 2.5 PRO LONG CONTEXT PERFORMANCE RESULTS")
    print("=" * 70)
    print(f"Input tokens (API):     {metrics.get('input_tokens', 0):,}")
    print(f"Output tokens (API):    {metrics.get('response_tokens', 0):,}")
    print(
        f"Total tokens:           {metrics.get('input_tokens', 0) + metrics.get('response_tokens', 0):,}"
    )
    print(f"First token latency:    {metrics.get('first_token_latency_ms', 0):.2f} ms")
    print(f"Total response time:    {metrics.get('total_response_time_ms', 0):.2f} ms")
    print(
        f"Processing speed:       {metrics.get('tokens_per_second', 0):.2f} tokens/sec"
    )

    # Calculate cost estimate (approximate pricing)
    input_tokens = metrics.get("input_tokens", 0)
    output_tokens = metrics.get("response_tokens", 0)
    # Gemini 2.0 Flash pricing (approximate): $0.075/1M input tokens, $0.30/1M output tokens
    input_cost = (input_tokens / 1_000_000) * 0.075
    output_cost = (output_tokens / 1_000_000) * 0.30
    total_cost = input_cost + output_cost
    print(f"Estimated cost:         ${total_cost:.4f} USD")
    print("=" * 70)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Gemini 2.5 Pro performance with long context input",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python context_test.py --book-path ./data/moby-dick.txt
  python context_test.py  # uses default ./data/book.txt

Recommended books by token count:
  - Alice in Wonderland: ~27k tokens (light test)
  - The Great Gatsby: ~50k tokens (medium test)  
  - Moby Dick: ~200k tokens (large test)
  - The Count of Monte Cristo: ~460k tokens (very large test)

Download from Project Gutenberg: https://www.gutenberg.org/
        """,
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
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY environment variable not set")
        print("Please set your Google API key:")
        print("export GOOGLE_API_KEY='your-api-key-here'")
        return

    # Load book text
    try:
        book_text = load_book_text(args.book_path)
    except Exception as e:
        print(f"ERROR: {e}")
        return

    # Run the test
    try:
        print(f"Starting Gemini long context performance test...")
        print(f"Book file: {args.book_path}")

        # Test basic performance with retry
        first_question = (
            args.question
            or "Please provide a brief summary of this book in 3-4 sentences."
        )
        metrics = await test_gemini_context_performance_with_retry(
            book_text, first_question
        )
        print_results(metrics)

        # Optional: Test with a different question if not provided custom question
        # if not args.question:
        #     print("\n" + "-" * 60)
        #     print("Testing with a different question...")
        #     time.sleep(60)

        #     custom_question = "Who are the main characters in this book and what are their relationships?"
        #     metrics2 = await test_gemini_context_performance_with_retry(
        #         book_text, custom_question
        #     )
        #     print_results(metrics2)

    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
