"""
AIWebScraper Smart Microservice Edition
FastAPI backend using a Web Extraction Engine for anti-bot Markdown extraction
and BYOK Google Gemini for intelligent JSON structuring.
"""

import os
import re
import json
import asyncio
import logging

import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# ──────────────────────────── Config ───────────────────────────────

load_dotenv()

EXTRACTOR_API_KEY = os.getenv("FIRECRAWL_API_KEY")
EXTRACTOR_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"

logger = logging.getLogger("aiwebscraper")

# ──────────────────────────── App Setup ────────────────────────────

app = FastAPI(
    title="AIWebScraper — Smart Microservice",
    description="WebExtractor + BYOK Gemini: scrape any page and get structured JSON.",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────── Models ───────────────────────────────

class ScrapeRequest(BaseModel):
    url: HttpUrl
    user_gemini_key: str


class MediaItem(BaseModel):
    url: str
    type: str | None = None  # "image" or "video"
    alt: str | None = None


class DataTable(BaseModel):
    title: str | None = None
    headers: list[str] = []
    rows: list[list[str]] = []


class StructuredResult(BaseModel):
    page_summary: str
    media: list[MediaItem] = []
    external_links: list[str] = []
    data_tables: list[DataTable] = []


class ScrapeResponse(BaseModel):
    url: str
    structured_data: StructuredResult
    raw_markdown: str


# ──────────────────────────── Extraction Step ─────────────────────

async def fetch_markdown_via_extractor(url: str) -> str:
    """Call the Web Extraction Engine to get clean Markdown from any URL."""
    if not EXTRACTOR_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: EXTRACTOR_API_KEY is not set.",
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EXTRACTOR_API_KEY}",
    }

    payload = {
        "url": url,
        "formats": ["markdown"],
        "timeout": 60000,
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            resp = await client.post(EXTRACTOR_SCRAPE_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            error_msg = e.response.text

            if status == 404:
                raise HTTPException(
                    status_code=404,
                    detail="The target webpage could not be found (404 Error). Please check the URL.",
                )
            elif status in (401, 403):
                raise HTTPException(
                    status_code=status,
                    detail="Access denied by the target website or extraction engine auth failed.",
                )
            elif status == 402:
                raise HTTPException(
                    status_code=502,
                    detail="Extraction engine API quota exceeded. Please try again later.",
                )
            else:
                raise HTTPException(
                    status_code=status,
                    detail=f"Scraping failed with status {status}: {error_msg[:500]}",
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach extraction engine: {str(exc)}",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred during scraping: {str(exc)}",
            )

    data = resp.json()

    # Extraction engine returns { success: true, data: { markdown: "..." } }
    markdown = data.get("data", {}).get("markdown", "")
    if not markdown:
        raise HTTPException(
            status_code=422,
            detail="Extraction engine returned no Markdown content for this URL.",
        )

    return markdown


# ──────────────────────────── Gemini Step ─────────────────────────

GEMINI_SYSTEM_PROMPT = """You are a data extraction assistant. Analyze the provided Markdown content from a web page and extract structured information.

Return a JSON object with EXACTLY these fields:
- "page_summary": A concise 2-3 sentence summary of what the page is about.
- "media": An array of objects with {"url": "...", "type": "image|video", "alt": "..."} for every image or video URL found in the Markdown.
- "external_links": An array of all external URLs (http/https links) found in the content.
- "data_tables": An array of structured data objects. Each object should have {"title": "...", "headers": ["col1", "col2"], "rows": [["val1", "val2"]]}. Use this for any pricing tables, product listings, comparison data, feature lists, or any other tabular/structured data you can identify.

Rules:
- For media, look for Markdown image syntax ![alt](url) and any raw image/video URLs.
- For external_links, extract all unique http/https URLs. Do NOT include image URLs here.
- For data_tables, be creative: if the page has a pricing section, product list, or any repeating structured pattern, organize it into a table format.
- If a field has no data, return an empty array [].
- Return ONLY the JSON object, no other text."""


async def structure_with_gemini(markdown: str, user_key: str) -> dict:
    """Configure Gemini on-the-fly with the user's BYOK key and structure the Markdown.
    Includes retry logic with exponential backoff for transient failures (503, 429)."""

    max_retries = 3
    base_delay = 2  # seconds

    # Initialize a per-request client with the user's key
    client = genai.Client(api_key=user_key)

    # Truncate very long markdown to stay within token limits
    max_chars = 100_000
    if len(markdown) > max_chars:
        markdown = markdown[:max_chars] + "\n\n[Content truncated for processing]"

    prompt = f"{GEMINI_SYSTEM_PROMPT}\n\nHere is the Markdown content to analyze:\n\n{markdown}"

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            result = json.loads(response.text)
            return result

        except json.JSONDecodeError:
            # Gemini returned something, but not valid JSON — no point retrying
            raise HTTPException(
                status_code=500,
                detail="Gemini returned invalid JSON. Please try again.",
            )
        except Exception as exc:
            last_exception = exc
            error_msg = str(exc).lower()

            # Auth errors — don't retry
            if "api key" in error_msg or "authenticate" in error_msg or "permission" in error_msg:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid Gemini API key. Please check your key and try again.",
                )

            # Transient errors (503 UNAVAILABLE, 429 rate limit) — retry
            if attempt < max_retries and ("503" in error_msg or "unavailable" in error_msg or "429" in error_msg or "resource" in error_msg or "overloaded" in error_msg):
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Gemini attempt {attempt}/{max_retries} failed (transient). Retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue

            # Non-transient or final attempt
            break

    # All retries exhausted — return None to signal fallback
    logger.warning(f"Gemini failed after {max_retries} attempts: {last_exception}")
    return None  # type: ignore


# ──────────────────────────── Fallback Parser ─────────────────────

def fallback_structure_from_markdown(markdown: str) -> dict:
    """Extract basic structured data from raw Markdown without any AI.
    Used as a fallback when Gemini is unavailable."""

    # Extract images: ![alt](url)
    image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    media = [
        {"url": m.group(2), "type": "image", "alt": m.group(1) or None}
        for m in image_pattern.finditer(markdown)
    ]

    # Extract links: [text](url) — exclude images
    link_pattern = re.compile(r'(?<!!)\[[^\]]*\]\((https?://[^)]+)\)')
    raw_url_pattern = re.compile(r'(?<!\()\bhttps?://[^\s)>\]"]+', re.IGNORECASE)

    link_urls = set(link_pattern.findall(markdown))
    raw_urls = set(raw_url_pattern.findall(markdown))
    image_urls = {m["url"] for m in media}
    external_links = sorted((link_urls | raw_urls) - image_urls)

    # Extract headings for a summary
    heading_pattern = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)
    headings = heading_pattern.findall(markdown)

    # Build a basic summary from headings
    if headings:
        page_summary = f"Page contains {len(headings)} sections: {', '.join(headings[:5])}{'...' if len(headings) > 5 else ''}. (Auto-parsed without AI — Gemini was unavailable.)"
    else:
        page_summary = "Page content was extracted successfully. (Auto-parsed without AI — Gemini was unavailable.)"

    # Try to find markdown tables
    data_tables = []
    table_pattern = re.compile(
        r'(\|.+\|\n\|[\s:|-]+\|\n(?:\|.+\|\n?)+)', re.MULTILINE
    )
    for match in table_pattern.finditer(markdown):
        lines = match.group(0).strip().split('\n')
        if len(lines) >= 3:
            headers = [h.strip() for h in lines[0].split('|') if h.strip()]
            rows = []
            for row_line in lines[2:]:  # skip header and separator
                cells = [c.strip() for c in row_line.split('|') if c.strip()]
                if cells:
                    rows.append(cells)
            if headers and rows:
                data_tables.append({
                    "title": "Extracted Table",
                    "headers": headers,
                    "rows": rows,
                })

    # If no tables found, create one from headings + first paragraph under each
    if not data_tables and headings:
        rows = [[h] for h in headings]
        data_tables.append({
            "title": "Page Sections",
            "headers": ["Section"],
            "rows": rows,
        })

    return {
        "page_summary": page_summary,
        "media": media,
        "external_links": external_links[:100],
        "data_tables": data_tables,
    }


# ──────────────────────────── Routes ──────────────────────────────

@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "aiwebscraper-smart-microservice",
        "version": "4.0.0",
    }


@app.post("/scrape-and-structure", response_model=ScrapeResponse)
async def scrape_and_structure(payload: ScrapeRequest):
    """
    Two-step pipeline:
    1. WebExtractor: URL → clean Markdown (server-side API key)
    2. Gemini:       Markdown → structured JSON (user's BYOK key)
    """
    url = str(payload.url)
    logger.info(f"Starting scrape-and-structure for: {url}")

    # Step 1: Scrape via WebExtractor
    raw_markdown = await fetch_markdown_via_extractor(url)
    logger.info(f"WebExtractor returned {len(raw_markdown)} chars of Markdown")

    # Step 2: Structure via Gemini (with retry + fallback)
    structured = await structure_with_gemini(raw_markdown, payload.user_gemini_key)

    # If Gemini is unavailable, fall back to regex-based parser
    if structured is None:
        logger.warning("Gemini unavailable — using fallback regex parser")
        structured = fallback_structure_from_markdown(raw_markdown)

    logger.info("Structuring complete")

    # Validate and build response
    structured_data = StructuredResult(
        page_summary=structured.get("page_summary", "No summary available."),
        media=[
            MediaItem(**m) if isinstance(m, dict) else MediaItem(url=str(m))
            for m in structured.get("media", [])
        ],
        external_links=structured.get("external_links", []),
        data_tables=[
            DataTable(**t) if isinstance(t, dict) else DataTable(title=str(t))
            for t in structured.get("data_tables", [])
        ],
    )

    return ScrapeResponse(
        url=url,
        structured_data=structured_data,
        raw_markdown=raw_markdown,
    )
