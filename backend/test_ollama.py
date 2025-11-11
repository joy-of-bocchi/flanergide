#!/usr/bin/env python3
"""Test script for Ollama integration."""

import asyncio
import sys
from app.services.summarizer import Summarizer


async def test_ollama():
    """Test Ollama summarizer with sample text."""
    print("=" * 80)
    print("Testing Ollama Integration")
    print("=" * 80)

    # Initialize summarizer
    try:
        summarizer = Summarizer(ollama_host="http://localhost:11434")
        print("\n✓ Summarizer initialized successfully")
    except Exception as e:
        print(f"\n✗ Failed to initialize summarizer: {e}")
        return False

    # Test with sample text
    sample_text = """
    Artificial intelligence (AI) is transforming how we work and live. Machine learning,
    a subset of AI, enables computers to learn from data without being explicitly programmed.
    Deep learning uses neural networks to process large amounts of unstructured data like images
    and text. These technologies are revolutionizing healthcare, finance, transportation, and education.
    However, they also raise important questions about privacy, bias, and ethical considerations that
    society must address carefully.
    """

    print("\n" + "-" * 80)
    print("Sample Text:")
    print("-" * 80)
    print(sample_text.strip())

    print("\n" + "-" * 80)
    print("Summarizing (this may take 30-60 seconds with Mistral)...")
    print("-" * 80)

    try:
        summary = await summarizer.summarize(sample_text, max_length=100)
        print(f"\n✓ Summary generated successfully!")
        print(f"\nSummary ({len(summary.split())} words):")
        print(summary)
        return True
    except Exception as e:
        print(f"\n✗ Failed to summarize: {e}")
        print("\nMake sure Ollama is running:")
        print("  1. Install Ollama from https://ollama.ai")
        print("  2. Open a terminal and run: ollama serve")
        print("  3. In another terminal, run: ollama pull mistral")
        print("  4. Run this script again")
        return False


async def main():
    """Run all tests."""
    success = await test_ollama()

    print("\n" + "=" * 80)
    if success:
        print("✓ All tests passed!")
        print("=" * 80)
        return 0
    else:
        print("✗ Tests failed. See error messages above.")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
