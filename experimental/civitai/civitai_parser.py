"""Parse Civitai model pages for prototype metadata extraction.

This experimental scraper pulls model details, creator metadata, stats, and
download links from Civitai HTML pages for local exploration.
"""

import json
import re
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class CivitaiParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def parse_model_page(self, url: str) -> Dict:
        """
        Parse a Civitai model page and extract key information.

        Args:
            url: The Civitai model page URL

        Returns:
            Dictionary containing parsed information
        """
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            result = {
                "url": url,
                "model_name": self._extract_model_name(soup),
                "tags": self._extract_tags(soup),
                "download_links": self._extract_download_links(soup),
                "details": self._extract_details(soup),
                "about": self._extract_about(soup),
                "stats": self._extract_stats(soup),
                "creator": self._extract_creator(soup),
                "license": self._extract_license(soup),
                "suggested_settings": self._extract_suggested_settings(soup),
                "version_info": self._extract_version_info(soup),
            }

            return result

        except requests.RequestException as e:
            return {"error": f"Failed to fetch page: {str(e)}"}
        except Exception as e:
            return {"error": f"Parsing error: {str(e)}"}

    def _extract_model_name(self, soup: BeautifulSoup) -> str:
        """Extract the model name from the page title or heading."""
        # Try to find the main heading
        heading = soup.find("h1") or soup.find("h2")
        if heading:
            return heading.get_text().strip()

        # Fallback to title tag
        title = soup.find("title")
        if title:
            return title.get_text().strip()

        return "Unknown Model"

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract model tags/categories."""
        tags = []

        # Look for tag elements with specific classes
        tag_elements = soup.find_all(
            ["a", "span"], class_=re.compile(r"tag|category|label")
        )
        for element in tag_elements:
            tag_text = element.get_text().strip()
            if (
                tag_text and len(tag_text) > 1 and len(tag_text) < 50
            ):  # Reasonable tag length
                tags.append(tag_text)

        # Look for tags in the details section specifically
        details_section = soup.find("div", class_=re.compile(r"details|info"))
        if details_section:
            detail_tags = details_section.find_all(
                ["a", "span"], class_=re.compile(r"tag|category")
            )
            for element in detail_tags:
                tag_text = element.get_text().strip()
                if tag_text and len(tag_text) > 1 and len(tag_text) < 50:
                    tags.append(tag_text)

        # Also look for common AI model tags
        tag_patterns = soup.find_all(
            string=re.compile(
                r"\b(anime|woman|girls|styles|base models|checkpoint|merge|illustrious)\b",
                re.IGNORECASE,
            )
        )
        for pattern in tag_patterns:
            if pattern.parent and pattern.parent.name in ["a", "span"]:
                tag_text = pattern.strip()
                if tag_text and tag_text not in tags and len(tag_text) < 50:
                    tags.append(tag_text)

        # Filter out navigation elements and common page elements
        filtered_tags = []
        exclude_words = [
            "home",
            "models",
            "images",
            "videos",
            "posts",
            "articles",
            "bounties",
            "challenges",
            "events",
            "updates",
            "shop",
            "create",
            "sign in",
            "pro",
            "more",
            "status",
            "safety",
            "newsroom",
            "api",
            "wiki",
            "education",
            "support",
            "terms",
            "privacy",
            "careers",
            "creators",
        ]

        for tag in tags:
            if tag.lower() not in [word.lower() for word in exclude_words]:
                filtered_tags.append(tag)

        return list(set(filtered_tags))  # Remove duplicates

    def _extract_download_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract download links and their metadata."""
        download_links = []

        # Look for download buttons and links
        download_elements = soup.find_all(
            ["a", "button"],
            href=re.compile(r"download|\.safetensors|\.ckpt|\.pt"),
            recursive=True,
        )

        # Also look for elements with download text
        download_text_elements = soup.find_all(
            ["a", "button"], string=re.compile(r"download", re.IGNORECASE)
        )

        # Combine both approaches
        all_elements = download_elements + download_text_elements

        for element in all_elements:
            link_info = {
                "url": element.get("href", ""),
                "text": element.get_text().strip(),
                "file_size": self._extract_file_size(element),
                "file_type": self._extract_file_type(element),
            }

            # Clean up the URL
            if link_info["url"] and not link_info["url"].startswith("http"):
                link_info["url"] = urljoin(
                    "https://civitai.com", link_info["url"]
                )

            # If no href, try to find a download link in the element or its children
            if not link_info["url"]:
                download_link = element.find(
                    "a", href=re.compile(r"download|\.safetensors|\.ckpt|\.pt")
                )
                if download_link:
                    link_info["url"] = download_link.get("href", "")
                    if link_info["url"] and not link_info["url"].startswith(
                        "http"
                    ):
                        link_info["url"] = urljoin(
                            "https://civitai.com", link_info["url"]
                        )

            if link_info["url"] and link_info["url"] not in [
                link["url"] for link in download_links
            ]:
                download_links.append(link_info)

        return download_links

    def _extract_file_size(self, element) -> str:
        """Extract file size from element or its siblings."""
        # Look for file size in the element or nearby text
        size_pattern = re.search(
            r"(\d+(?:\.\d+)?\s*(?:GB|MB|KB))", element.get_text(), re.IGNORECASE
        )
        if size_pattern:
            return size_pattern.group(1)
        return ""

    def _extract_file_type(self, element) -> str:
        """Extract file type from element."""
        href = element.get("href", "")
        if ".safetensors" in href:
            return "SafeTensor"
        elif ".ckpt" in href:
            return "Checkpoint"
        elif ".pt" in href:
            return "PyTorch"
        return ""

    def _extract_details(self, soup: BeautifulSoup) -> Dict:
        """Extract details section information."""
        details = {}

        # Look for details table or structured information
        detail_tables = soup.find_all("table")
        for table in detail_tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip()
                    value = cells[1].get_text().strip()
                    if key and value:
                        details[key] = value

        # Also look for any structured data
        structured_data = soup.find_all("script", type="application/ld+json")
        for script in structured_data:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    details.update(data)
            except (json.JSONDecodeError, TypeError):
                continue

        return details

    def _extract_about(self, soup: BeautifulSoup) -> str:
        """Extract about/description information."""
        about_text = ""

        # Look for about section
        about_sections = soup.find_all(
            ["div", "section"], class_=re.compile(r"about|description|content")
        )

        for section in about_sections:
            text = section.get_text().strip()
            if len(text) > len(about_text):
                about_text = text

        # Also look for any paragraph with substantial content
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50 and len(text) > len(about_text):
                about_text = text

        return about_text

    def _extract_stats(self, soup: BeautifulSoup) -> Dict:
        """Extract model statistics."""
        stats = {}

        # Look for stats in various formats
        stat_elements = soup.find_all(
            string=re.compile(r"\d+[km]?", re.IGNORECASE)
        )
        for element in stat_elements:
            if element.parent:
                parent_text = element.parent.get_text()
                # Try to identify what the stat represents
                if "download" in parent_text.lower():
                    stats["downloads"] = element.strip()
                elif "like" in parent_text.lower():
                    stats["likes"] = element.strip()
                elif "comment" in parent_text.lower():
                    stats["comments"] = element.strip()

        return stats

    def _extract_creator(self, soup: BeautifulSoup) -> str:
        """Extract creator information."""
        creator = ""

        # Look for creator links or mentions
        creator_elements = soup.find_all(
            ["a", "span"], class_=re.compile(r"creator|author|artist")
        )

        for element in creator_elements:
            text = element.get_text().strip()
            if text and len(text) < 50:  # Reasonable creator name length
                creator = text
                break

        return creator

    def _extract_license(self, soup: BeautifulSoup) -> str:
        """Extract license information."""
        license_text = ""

        # Look for license information
        license_elements = soup.find_all(
            string=re.compile(r"license", re.IGNORECASE)
        )
        for element in license_elements:
            if element.parent:
                text = element.parent.get_text().strip()
                if "license" in text.lower():
                    license_text = text
                    break

        return license_text

    def _extract_suggested_settings(self, soup: BeautifulSoup) -> Dict:
        """Extract suggested settings information."""
        settings = {}

        # Look for settings information
        settings_sections = soup.find_all(
            string=re.compile(r"suggested|settings|cfg|sampler", re.IGNORECASE)
        )

        for element in settings_sections:
            if element.parent:
                parent_text = element.parent.get_text()
                if "suggested" in parent_text.lower():
                    settings["suggested_settings"] = parent_text.strip()
                    break

        return settings

    def _extract_version_info(self, soup: BeautifulSoup) -> Dict:
        """Extract version information."""
        version_info = {}

        # Look for version information
        version_elements = soup.find_all(
            string=re.compile(r"v\d+\.\d+", re.IGNORECASE)
        )
        for element in version_elements:
            version_match = re.search(r"v(\d+\.\d+)", element, re.IGNORECASE)
            if version_match:
                version_info["version"] = version_match.group(1)
                break

        return version_info


def main():
    """Example usage of the CivitaiParser."""
    parser = CivitaiParser()

    # Example URL
    url = "https://civitai.com/models/1224788/prefect-illustrious-xl"

    print("Parsing Civitai model page...")
    result = parser.parse_model_page(url)

    # Print the result in a formatted way
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
