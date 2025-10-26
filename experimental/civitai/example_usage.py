#！/usr/bin/env python3
"""
Example usage of the CivitaiParser to extract information from Civitai model pages.
"""

from civitai_parser import CivitaiParser
import json


def main():
# 初始化解析器
    parser = CivitaiParser()
# 要测试的示例 URL
    urls = [
        "https://civitai.com/models/1224788/prefect-illustrious-xl",
# 在此添加更多URL进行测试
    ]

    for url in urls:
        print(f"\n{'='*60}")
        print(f"Parsing: {url}")
        print(f"{'='*60}")
# 解析模型页面
        result = parser.parse_model_page(url)
# 保存到 JSON 文件
        filename = f"civitai_model_{url.split('/')[-1]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Results saved to: {filename}")
# Print 关键信息
        if "error" not in result:
            print(f"\nModel Name: {result.get('model_name', 'N/A')}")
            print(f"Creator: {result.get('creator', 'N/A')}")
            print(f"Tags: {', '.join(result.get('tags', []))}")
            print(f"Download Links: {len(result.get('download_links', []))}")
            print(f"Stats: {result.get('stats', {})}")
            print(f"Version: {result.get('version_info', {}).get('version', 'N/A')}")
# Print 关于部分（已截断）
            about = result.get("about", "")
            if about:
                print(f"\nAbout (first 200 chars): {about[:200]}...")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
