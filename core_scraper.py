"""
WebExtractor — Traditional Web Data Extraction Module

A standard implementation of a web scraping utility using conventional
HTTP requests and HTML parsing. Designed for structured data extraction
from static web pages with proper error handling and rate limiting.

Usage:
    python core_scraper.py --url https://example.com
"""

import json
import sys
import logging
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ──────────────────────────── Configuration ───────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Standard browser User-Agent to prevent basic request blocking
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Default output file path
OUTPUT_FILE = "raw_dataset.json"


# ──────────────────────────── WebExtractor Class ──────────────────

class WebExtractor:
    """
    A traditional web scraper that fetches and parses HTML content
    from a given URL. Extracts page metadata, headings, paragraph
    text, and hyperlinks using standard HTTP requests and DOM parsing.

    Attributes:
        url (str): The target URL to scrape.
        headers (dict): HTTP headers to include with the request.
        soup (BeautifulSoup | None): Parsed DOM tree of the page.
        raw_html (str): The raw HTML response body.
    """

    def __init__(self, url: str, headers: Optional[dict] = None):
        """
        Initialize the WebExtractor with a target URL.

        Args:
            url: The webpage URL to extract data from.
            headers: Optional custom HTTP headers. Falls back to
                     a standard browser User-Agent if not provided.
        """
        self.url = url
        self.headers = headers or DEFAULT_HEADERS
        self.soup: Optional[BeautifulSoup] = None
        self.raw_html: str = ""

    def fetch_data(self) -> bool:
        """
        Send an HTTP GET request to the target URL and store the
        raw HTML response. Includes error handling for network
        failures, timeouts, and non-200 status codes.

        Returns:
            True if the page was successfully fetched, False otherwise.
        """
        logger.info("Fetching URL: %s", self.url)

        try:
            response = requests.get(
                self.url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()

        except requests.exceptions.Timeout:
            logger.error("Request timed out after %d seconds.", REQUEST_TIMEOUT)
            return False

        except requests.exceptions.ConnectionError:
            logger.error("Failed to establish a connection to %s.", self.url)
            return False

        except requests.exceptions.HTTPError as http_err:
            logger.error(
                "HTTP error %d: %s", response.status_code, str(http_err)
            )
            return False

        except requests.exceptions.RequestException as req_err:
            logger.error("An unexpected request error occurred: %s", str(req_err))
            return False

        # Store raw HTML and confirm success
        self.raw_html = response.text
        logger.info(
            "Successfully fetched %d characters (HTTP %d).",
            len(self.raw_html),
            response.status_code,
        )
        return True

    def parse_html(self) -> dict:
        """
        Parse the fetched HTML content and extract structured data
        including the page title, all h2 headings, paragraph text,
        and anchor links.

        Returns:
            A dictionary containing the extracted data fields:
            - title: The page <title> text
            - h2_headings: List of all <h2> tag contents
            - paragraphs: List of all <p> tag text content
            - links: List of dicts with 'text' and 'href' keys
            - metadata: Extraction timestamp and source URL
        """
        if not self.raw_html:
            logger.warning("No HTML content to parse. Call fetch_data() first.")
            return {}

        logger.info("Parsing HTML with BeautifulSoup...")
        self.soup = BeautifulSoup(self.raw_html, "html.parser")

        # Extract page title
        title_tag = self.soup.find("title")
        page_title = title_tag.get_text(strip=True) if title_tag else "Untitled"

        # Extract all h2 headings
        h2_tags = self.soup.find_all("h2")
        h2_headings = [
            tag.get_text(strip=True)
            for tag in h2_tags
            if tag.get_text(strip=True)
        ]

        # Extract paragraph text content
        p_tags = self.soup.find_all("p")
        paragraphs = [
            tag.get_text(strip=True)
            for tag in p_tags
            if tag.get_text(strip=True)
        ]

        # Extract hyperlinks with their text and href attributes
        a_tags = self.soup.find_all("a", href=True)
        links = [
            {
                "text": tag.get_text(strip=True) or "[No text]",
                "href": tag["href"],
            }
            for tag in a_tags
            if tag["href"].startswith(("http://", "https://"))
        ]

        # Build the structured result
        result = {
            "title": page_title,
            "h2_headings": h2_headings,
            "paragraphs": paragraphs,
            "links": links,
            "metadata": {
                "source_url": self.url,
                "extracted_at": datetime.now().isoformat(),
                "total_headings": len(h2_headings),
                "total_paragraphs": len(paragraphs),
                "total_links": len(links),
                "html_length": len(self.raw_html),
            },
        }

        logger.info(
            "Extraction complete: %d headings, %d paragraphs, %d links.",
            len(h2_headings),
            len(paragraphs),
            len(links),
        )
        return result


# ──────────────────────────── Utility Functions ───────────────────

def save_to_json(data: dict, filepath: str = OUTPUT_FILE) -> None:
    """
    Serialize the extracted data dictionary to a JSON file
    with human-readable formatting.

    Args:
        data: The structured data dictionary to save.
        filepath: Output file path (default: raw_dataset.json).
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Data saved to %s", filepath)


# ──────────────────────────── Main Entry Point ────────────────────

if __name__ == "__main__":
    # Accept URL from command-line argument or use a default
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = "https://example.com"
        logger.info("No URL provided. Using default: %s", target_url)

    # Initialize the extractor
    extractor = WebExtractor(url=target_url)

    # Step 1: Fetch the page HTML
    if not extractor.fetch_data():
        logger.error("Failed to fetch the target page. Exiting.")
        sys.exit(1)

    # Step 2: Parse the HTML and extract structured data
    extracted_data = extractor.parse_html()

    if not extracted_data:
        logger.error("HTML parsing returned no data. Exiting.")
        sys.exit(1)

    # Step 3: Save results to JSON
    save_to_json(extracted_data)

    # Print a summary to the console
    print("\n" + "=" * 50)
    print(f"  WebExtractor — Extraction Summary")
    print("=" * 50)
    print(f"  Source:      {extracted_data['metadata']['source_url']}")
    print(f"  Title:       {extracted_data['title']}")
    print(f"  Headings:    {extracted_data['metadata']['total_headings']}")
    print(f"  Paragraphs:  {extracted_data['metadata']['total_paragraphs']}")
    print(f"  Links:       {extracted_data['metadata']['total_links']}")
    print(f"  Output:      {OUTPUT_FILE}")
    print("=" * 50 + "\n")
