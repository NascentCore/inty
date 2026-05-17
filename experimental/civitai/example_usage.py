#!/usr/bin/env python3
"""
Example usage of the CivitaiParser to extract information from Civitai model pages.
"""

from civitai_parser import CivitaiParser
import json


def main():
    # Initialize the parser
    parser = CivitaiParser()

    # Example URLs to test
    urls = [
        "https://civitai.com/models/1224788/prefect-illustrious-xl",
        # Add more URLs here for testing
    ]

    for url in urls:
        print(f"\n{'='*60}")
        print(f"Parsing: {url}")
        print(f"{'='*60}")

        # Parse the model page
        result = parser.parse_model_page(url)

        # Save to JSON file
        filename = f"civitai_model_{url.split('/')[-1]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Results saved to: {filename}")

        # Print key information
        if "error" not in result:
            print(f"\nModel Name: {result.get('model_name', 'N/A')}")
            print(f"Creator: {result.get('creator', 'N/A')}")
            print(f"Tags: {', '.join(result.get('tags', []))}")
            print(f"Download Links: {len(result.get('download_links', []))}")
            print(f"Stats: {result.get('stats', {})}")
            print(
                f"Version: {result.get('version_info', {}).get('version', 'N/A')}"
            )

            # Print about section (truncated)
            about = result.get("about", "")
            if about:
                print(f"\nAbout (first 200 chars): {about[:200]}...")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
