"""
AIWebScraper Smart Microservice — v8.0
FastAPI backend: Firecrawl + BYOK Gemini + Two-Pass Classification.

Changes in v8:
- Rate limiting: 10 extractions/day per Gemini key (in-memory, resets at UTC midnight)
- New /search-and-structure endpoint using Firecrawl /v1/search
- Two-Pass architecture: Pass 1 classifies page type (5k chars, fast),
  Pass 2 extracts with a schema-aware prompt tuned to the page type
- DIRECTORY_OR_LIST pages get a hard 20-item cap to prevent JSON truncation
- Classifier uses response_schema for native JSON enforcement
- JSON parsing wrapped in try/except with partial-JSON recovery
"""

import os
import re
import json
import hashlib
import asyncio
import logging
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ──────────────────────────── Config ───────────────────────────────

load_dotenv()

FIRECRAWL_API_KEY    = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v1/search"

logger = logging.getLogger("aiwebscraper")
logging.basicConfig(level=logging.INFO)

_thread_pool = ThreadPoolExecutor(max_workers=6)

# ──────────────────────────── Rate Limiter ─────────────────────────
# In-memory daily rate limiter keyed by a short hash of the Gemini key.
# Resets automatically when the UTC date changes.

DAILY_LIMIT = 10
usage_tracker: dict[str, dict] = {}


def _key_id(gemini_key: str) -> str:
    """Return a short non-reversible identifier derived from the API key."""
    return hashlib.sha256(gemini_key.strip().encode()).hexdigest()[:16]


def check_rate_limit(gemini_key: str) -> None:
    """
    Raise HTTP 429 if this key has already hit DAILY_LIMIT today.
    Increments the counter on every successful check.
    Thread-safe for single-process deployments (asyncio event loop is single-threaded).
    """
    today = str(date.today())
    kid = _key_id(gemini_key)
    entry = usage_tracker.get(kid)
    if entry is None or entry["date"] != today:
        usage_tracker[kid] = {"date": today, "count": 0}
    if usage_tracker[kid]["count"] >= DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily limit of {DAILY_LIMIT} extractions per API key reached. "
                "Resets at midnight UTC."
            ),
        )
    usage_tracker[kid]["count"] += 1


# ──────────────────────────── App Setup ────────────────────────────

app = FastAPI(
    title="AIWebScraper — Smart Microservice",
    description="Firecrawl + BYOK Gemini 2.5 Flash: scrape or search any page, get structured JSON.",
    version="8.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────── Request / Response Models ────────────

class ScrapeRequest(BaseModel):
    url: str
    user_gemini_key: str


class SearchRequest(BaseModel):
    query: str
    user_gemini_key: str


class MediaItem(BaseModel):
    url: str
    type: str | None = None
    alt: str | None = None


class LinkItem(BaseModel):
    text: str
    url: str


class DataTable(BaseModel):
    title: str | None = None
    headers: list[str] = []
    rows: list[list[str]] = []


class StructuredResult(BaseModel):
    page_title: str = ""
    page_summary: str = ""
    headings: list[str] = []
    paragraphs: list[str] = []
    media: list[MediaItem] = []
    links: list[LinkItem] = []
    external_links: list[str] = []
    data_tables: list[DataTable] = []


class ScrapeResponse(BaseModel):
    url: str
    page_type: str = "GENERAL"
    structured_data: StructuredResult
    raw_markdown: str


class SearchResponse(BaseModel):
    query: str
    sources: list[str] = []
    page_type: str = "GENERAL"
    structured_data: StructuredResult
    combined_markdown: str


# ──────────────────────────── Pydantic Schema for Classifier ───────

class _PageClassification(BaseModel):
    """Minimal schema used ONLY for the Pass-1 classifier response."""
    page_type: str   # ECOMMERCE | ARTICLE | DIRECTORY_OR_LIST | GENERAL


PAGE_TYPES = {"ECOMMERCE", "ARTICLE", "DIRECTORY_OR_LIST", "GENERAL"}


# ──────────────────────────── Markdown Pre-Cleaner ─────────────────

_CLEAN_BR          = re.compile(r"<br\s*/?>",       re.IGNORECASE)
_CLEAN_BOLD        = re.compile(r"</?b>",           re.IGNORECASE)
_CLEAN_ITALIC      = re.compile(r"</?i>",           re.IGNORECASE)
_CLEAN_SPAN        = re.compile(r"</?span[^>]*>",   re.IGNORECASE)
_CLEAN_ANCHOR      = re.compile(r"<a\s[^>]*>|</a>", re.IGNORECASE)
_CLEAN_TAGS        = re.compile(r"<[^>]+>")
_CLEAN_NBSP        = re.compile(r"&nbsp;")
_CLEAN_AMP         = re.compile(r"&amp;")
_CLEAN_ENTITIES    = re.compile(r"&[a-zA-Z]{2,8};")
_CLEAN_SPACES      = re.compile(r"[ \t]{2,}")
_CLEAN_BLANK_LINES = re.compile(r"\n{3,}")


def _pre_clean_markdown(text: str) -> str:
    text = _CLEAN_BR.sub("\n", text)
    text = _CLEAN_BOLD.sub("", text)
    text = _CLEAN_ITALIC.sub("", text)
    text = _CLEAN_SPAN.sub("", text)
    text = _CLEAN_ANCHOR.sub("", text)
    text = _CLEAN_TAGS.sub("", text)
    text = _CLEAN_NBSP.sub(" ", text)
    text = _CLEAN_AMP.sub("&", text)
    text = _CLEAN_ENTITIES.sub("", text)
    text = _CLEAN_SPACES.sub(" ", text)
    text = _CLEAN_BLANK_LINES.sub("\n\n", text)
    return text.strip()


def _smart_truncate(text: str, max_chars: int = 1_000_000) -> str:
    """Keep head 70% + tail 30% so footer/metadata is not lost."""
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.70)
    tail = int(max_chars * 0.30)
    return text[:head] + "\n\n[...middle content omitted for length...]\n\n" + text[-tail:]


# ──────────────────────────── Helpers ─────────────────────────────

def _is_amazon_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        return "amazon." in host or host.endswith(".amazon.com")
    except Exception:
        return False


# ──────────────────────────── Jina AI Fallback ────────────────────

async def fetch_markdown_via_jina(url: str) -> str:
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "text/markdown, text/plain, */*",
        "X-Return-Format": "markdown",
        "X-Timeout": "30",
        "X-With-Generated-Alt": "true",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(jina_url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            text = resp.text.strip()
            if text and len(text) > 100:
                logger.info(f"Jina fallback succeeded: {len(text)} chars")
                return text
            raise HTTPException(status_code=422, detail="Jina AI could not extract content from this page.")
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=422, detail="Both Firecrawl and Jina AI failed to load this page.")
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Failed to reach Jina AI fallback service.")


# ──────────────────────────── Firecrawl Scrape ─────────────────────

async def fetch_markdown_via_firecrawl(url: str) -> tuple[str, list[dict]]:
    """Returns (markdown, links_list)."""
    if not FIRECRAWL_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfiguration: FIRECRAWL_API_KEY is not set.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
    }

    payload: dict = {
        "url": url,
        "formats": ["markdown", "links"],
        "onlyMainContent": True,
        "removeBase64Images": True,
        "skipTlsVerification": True,
        "timeout": 90000,
        "waitFor": 5000,
    }

    if _is_amazon_url(url):
        payload["mobile"] = True
        payload["waitFor"] = 6000
        payload["timeout"] = 120000
        payload["actions"] = [
            {"type": "wait", "milliseconds": 4000},
            {"type": "scroll", "direction": "down", "amount": 1200},
            {"type": "wait", "milliseconds": 2000},
            {"type": "scroll", "direction": "down", "amount": 1200},
            {"type": "wait", "milliseconds": 1000},
        ]

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(FIRECRAWL_SCRAPE_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            error_body = {}
            try:
                error_body = e.response.json()
            except Exception:
                pass
            if status == 404:
                raise HTTPException(status_code=404, detail="The target webpage could not be found (404).")
            elif status in (401, 403):
                raise HTTPException(status_code=status, detail="Access denied by the target website or Firecrawl auth failed.")
            elif status == 402:
                raise HTTPException(status_code=502, detail="Firecrawl API quota exceeded.")
            elif status in (408, 500, 502, 503):
                logger.warning(f"Firecrawl returned {status} — falling back to Jina AI")
                fallback_md = await fetch_markdown_via_jina(url)
                return fallback_md, []
            else:
                raise HTTPException(
                    status_code=status,
                    detail=f"Firecrawl error {status}: {error_body.get('error', e.response.text[:300])}",
                )
        except httpx.TimeoutException:
            logger.warning("Firecrawl timed out — falling back to Jina AI")
            fallback_md = await fetch_markdown_via_jina(url)
            return fallback_md, []
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to reach Firecrawl: {str(exc)}")

    data = resp.json()
    if not data.get("success"):
        error_msg = data.get("error", "")
        logger.warning(f"Firecrawl success=false: {error_msg} — trying Jina fallback")
        fallback_md = await fetch_markdown_via_jina(url)
        return fallback_md, []

    page_data = data.get("data", {})
    markdown = page_data.get("markdown", "")
    links = page_data.get("links", [])

    if not markdown:
        raise HTTPException(status_code=422, detail="Firecrawl returned no content. The page may require login or is empty.")

    return markdown, links


# ──────────────────────────── Firecrawl Search ─────────────────────

async def search_via_firecrawl(query: str) -> tuple[list[str], list[str]]:
    """
    Search using Firecrawl /v1/search. Returns (markdowns_list, source_urls_list).
    Pulls top 3 results and returns their markdown content.
    """
    if not FIRECRAWL_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfiguration: FIRECRAWL_API_KEY is not set.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
    }

    payload = {
        "query": query,
        "limit": 3,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True,
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(FIRECRAWL_SEARCH_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            raise HTTPException(
                status_code=status,
                detail=f"Firecrawl search failed ({status}). Check your API key or query.",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to reach Firecrawl search: {str(exc)}")

    data = resp.json()
    if not data.get("success"):
        raise HTTPException(status_code=502, detail=f"Firecrawl search returned success=false: {data.get('error', '')}")

    results = data.get("data", [])
    markdowns: list[str] = []
    sources: list[str] = []

    for result in results[:3]:
        md = result.get("markdown", "").strip()
        url = result.get("url") or result.get("metadata", {}).get("sourceURL", "")
        if md:
            markdowns.append(md)
        if url:
            sources.append(url)

    if not markdowns:
        raise HTTPException(status_code=422, detail=f"Firecrawl search returned no readable content for: '{query}'")

    return markdowns, sources


# ──────────────────────────── Gemini System Prompt ─────────────────

GEMINI_SYSTEM_PROMPT = """\
You are an expert data extraction assistant. Analyze the provided Markdown content from a web page and extract structured information exhaustively.

Return a strictly valid JSON object with EXACTLY these fields:

{
  "page_title": "The main title or name of the page (from H1 or the first heading)",
  "page_summary": "A concise 2-3 sentence summary of what the page is about.",
  "headings": ["Every heading found on the page (H1, H2, H3, H4) as plain text strings, in document order"],
  "paragraphs": ["Every meaningful paragraph of body text, cleaned of markdown symbols. Each item is one paragraph."],
  "media": [
    {"url": "full image/video URL", "type": "image or video", "alt": "alt text or description"}
  ],
  "links": [
    {"text": "The visible link text — NEVER the raw URL as text", "url": "full https://... URL"}
  ],
  "external_links": ["array of unique external http/https URLs found in content"],
  "data_tables": [
    {
      "title": "Table name/context",
      "headers": ["Column1", "Column2"],
      "rows": [["value1", "value2"]]
    }
  ]
}

CRITICAL INSTRUCTIONS — violate none:

1. BE EXHAUSTIVE: Do not summarize lists. Extract EVERY single image, EVERY link, and EVERY row of data you can find. Never output "..." or "etc" to cut corners. If a page has 50 paragraphs, return all 50.

2. DATA TABLES: Aggressively group repeating patterns (pricing, specs, feature lists, reviews, product grids, cast lists, FAQs, comparison tables) into the data_tables array.

3. CLEAN MARKDOWN LINKS: Never output raw markdown like [Text](URL). For the links array, extract the visible text as "text" and the URL as "url". Example: [Leonardo DiCaprio](https://...) → {"text": "Leonardo DiCaprio", "url": "https://..."}.

4. ALL row cell values MUST be plain text strings. Never put objects, arrays, or nulls inside a row cell. If a cell is empty, use an empty string "".

5. HEADINGS: Include every H1–H4 as a plain text string. Strip all # symbols.

6. PARAGRAPHS: Strip all markdown symbols (**, *, _, #, >, -) from paragraph text. Return clean readable sentences.

7. MEDIA: Find every image using ![alt](url) syntax AND any raw image URLs (.jpg, .png, .gif, .webp, .svg). Find video embeds too.

8. NO MARKDOWN IN OUTPUT: All string values must be plain text — no **, *, _, #, >, or backtick characters inside values.

9. Output ONLY raw, parseable JSON. Do not wrap it in ```json fences or any markdown block. No commentary, no explanation.

10. If a field has no data, return an empty array [].\
"""

# Extra instruction injected for DIRECTORY pages to prevent JSON truncation
_DIRECTORY_CAP = (
    "\n\nCRITICAL PREVENT TRUNCATION: This is a massive list/directory page. "
    "You MUST stop extracting after a maximum of 20 items total across all arrays. "
    "Do NOT attempt to extract the entire page — the output will truncate and fail. "
    "Extract the BEST 20 items and stop."
)

# Classifier prompt
_CLASSIFIER_PROMPT = """\
Classify this web page into exactly one of these categories:
- ECOMMERCE: Product listings, shopping pages, item details with prices, online stores.
- ARTICLE: News articles, blog posts, Wikipedia pages, documentation, tutorials.
- DIRECTORY_OR_LIST: Index pages, torrents sites, link directories, search result pages, massive item lists.
- GENERAL: Everything else (homepages, portfolios, contact pages, etc.)

Return ONLY valid JSON with a single field "page_type".

Page preview (first 5,000 characters):
"""


# ──────────────────────────── Pass 1: Classifier ───────────────────

def _classify_page_sync(preview: str, user_key: str) -> str:
    """Fast classifier — runs on first 5k chars, returns page_type string."""
    client = genai.Client(api_key=user_key)
    prompt = _CLASSIFIER_PROMPT + preview

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_PageClassification,
            temperature=0.0,
            max_output_tokens=64,
        ),
    )
    try:
        result = json.loads(response.text)
        page_type = result.get("page_type", "GENERAL").upper()
        return page_type if page_type in PAGE_TYPES else "GENERAL"
    except (json.JSONDecodeError, AttributeError):
        return "GENERAL"


async def classify_page(markdown: str, user_key: str) -> str:
    """Async wrapper for the classifier. Defaults to GENERAL on any failure."""
    preview = _pre_clean_markdown(markdown)[:5000]
    loop = asyncio.get_event_loop()
    try:
        page_type = await loop.run_in_executor(_thread_pool, _classify_page_sync, preview, user_key)
        logger.info(f"Page classified as: {page_type}")
        return page_type
    except Exception as exc:
        logger.warning(f"Classifier failed ({exc}) — defaulting to GENERAL")
        return "GENERAL"


# ──────────────────────────── Pass 2: Extractor ────────────────────

def _call_gemini_sync(markdown: str, user_key: str, page_type: str = "GENERAL") -> str:
    """
    Main extraction call — runs in a thread executor.
    Uses genai.Client (instance-scoped, thread-safe, no global configure() race).
    Injects a 20-item cap instruction for DIRECTORY_OR_LIST pages.
    """
    client = genai.Client(api_key=user_key)

    cleaned = _pre_clean_markdown(markdown)
    truncated = _smart_truncate(cleaned, max_chars=1_000_000)

    logger.info(f"[{page_type}] Sending {len(truncated)} chars to Gemini (from {len(markdown)} raw)")

    extra = _DIRECTORY_CAP if page_type == "DIRECTORY_OR_LIST" else ""
    prompt = f"{GEMINI_SYSTEM_PROMPT}{extra}\n\nExtract ALL data from this web page markdown:\n\n{truncated}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=8192,
        ),
    )
    return response.text


async def structure_with_gemini(
    markdown: str, user_key: str, page_type: str = "GENERAL"
) -> tuple[dict | None, str | None]:
    """
    Run Gemini extraction in a thread pool.
    Returns (result_dict, error_message).
    error_message is None on success, or a human-readable reason on failure.
    JSON parsing wrapped in try/except with partial-JSON recovery.
    """
    max_retries = 3
    base_delay = 2
    last_error_msg: str | None = None
    raw_text: str = ""

    for attempt in range(1, max_retries + 1):
        try:
            loop = asyncio.get_event_loop()
            raw_text = await loop.run_in_executor(
                _thread_pool, _call_gemini_sync, markdown, user_key, page_type
            )

            # Strip accidental markdown fences
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned).strip()

            result = json.loads(cleaned)
            logger.info("Gemini extraction succeeded on attempt %d (page_type=%s)", attempt, page_type)
            return result, None

        except json.JSONDecodeError as exc:
            logger.warning(f"Gemini JSON parse failed (attempt {attempt}): {exc}")
            # --- Graceful partial-JSON recovery ---
            # Try to salvage a complete top-level object from truncated output
            try:
                # Find the outermost { ... } block
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    candidate = match.group(0)
                    result = json.loads(candidate)
                    logger.info("Partial JSON recovery succeeded")
                    return result, None
            except Exception:
                pass
            # If recovery failed, truncate arrays that may have broken JSON
            try:
                # Remove trailing incomplete array/object by cutting at last full value
                truncated_attempt = re.sub(r',\s*"[^"]*"\s*:\s*\[.*$', '', raw_text, flags=re.DOTALL)
                truncated_attempt = truncated_attempt.rstrip(", \n\r\t") + "}"
                result = json.loads(truncated_attempt)
                logger.info("Truncated JSON recovery succeeded")
                return result, None
            except Exception:
                pass
            last_error_msg = f"Gemini returned malformed JSON: {exc}"
            break  # No point retrying bad JSON

        except Exception as exc:
            last_error_msg = str(exc)
            error_lower = last_error_msg.lower()
            logger.warning(f"Gemini attempt {attempt}/{max_retries} error: {exc}")

            # Auth errors — surface immediately
            if any(k in error_lower for k in ("api key", "api_key", "authenticate", "permission denied", "invalid")):
                return None, f"Invalid or missing Gemini API key. Please update your key in settings. ({exc})"

            # Region/access errors
            if "user location" in error_lower or "not supported" in error_lower:
                return None, f"Gemini not available in your region or for this key tier. ({exc})"

            # Transient errors — retry with backoff
            is_transient = any(k in error_lower for k in (
                "503", "unavailable", "429", "resource", "overloaded", "quota", "exhausted"
            ))
            if is_transient and attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Transient error — retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            break

    logger.warning(f"Gemini failed after {max_retries} attempts: {last_error_msg}")
    return None, last_error_msg


# ──────────────────────────── Fallback Regex Parser ────────────────

_MD_LINK  = re.compile(r'\[([^\]]+)\]\((https?://[^)\s"]+)[^)]*\)')
_MD_IMG   = re.compile(r'!\[([^\]]*)\]\((https?://[^)\s"]+)[^)]*\)')
_RAW_URL  = re.compile(r'(?<!\()\bhttps?://[^\s)<>\]"]+')
_HEADING  = re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE)
_BULLET   = re.compile(r'^[\-\*•]\s+(.{10,300})$', re.MULTILINE)
_PRICE    = re.compile(r'[\u20b9$€£]\s?[\d,]+(?:\.\d{1,2})?|\b(?:INR|USD|EUR|GBP)\s?[\d,]+(?:\.\d{1,2})?', re.IGNORECASE)
_RATING   = re.compile(r'([\d.]+)\s*(?:out of 5|/5|stars?|\u2605)', re.IGNORECASE)
_TABLE    = re.compile(r'(\|.+\|\n\|[\s:|-]+\|\n(?:\|.+\|\n?)+)', re.MULTILINE)
_PARA     = re.compile(r'(?:^|\n\n)([A-Z][^\n]{60,}(?:\n[^\n]+)*)', re.MULTILINE)


def _clean_md_link_text(text: str) -> str:
    text = _MD_IMG.sub(r"[Image: \1]", text)
    text = _MD_LINK.sub(r"\1", text)
    return text.strip()


def _sanitize_cell(text: str) -> str:
    """Strip HTML tags and markdown links from a table cell."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text.strip()


def fallback_structure_from_markdown(markdown: str, error_msg: str | None = None) -> dict:
    """Comprehensive fallback regex parser when Gemini is unavailable."""

    media = [
        {"url": m.group(2), "type": "image", "alt": m.group(1) or ""}
        for m in _MD_IMG.finditer(markdown)
        if not m.group(2).endswith(('.svg', '.ico'))
    ][:30]

    links = []
    seen_urls: set[str] = set()
    for m in _MD_LINK.finditer(markdown):
        txt, url = m.group(1).strip(), m.group(2).strip()
        if url not in seen_urls and txt and not txt.startswith("http"):
            links.append({"text": txt, "url": url})
            seen_urls.add(url)
    links = links[:80]

    image_urls = {item["url"] for item in media}
    captured_urls = {l["url"] for l in links}
    raw_urls = [u for u in _RAW_URL.findall(markdown) if u not in image_urls and u not in captured_urls]
    external_links = sorted(set(raw_urls))[:80]

    headings = [m.group(2).strip() for m in _HEADING.finditer(markdown)][:40]

    paragraphs = []
    for m in _PARA.finditer(markdown):
        raw = m.group(1).strip()
        cleaned = _clean_md_link_text(raw)
        cleaned = re.sub(r"[*_`#>]", "", cleaned).strip()
        if len(cleaned) > 40 and cleaned not in paragraphs:
            paragraphs.append(cleaned)
    paragraphs = paragraphs[:60]

    page_title = headings[0] if headings else ""
    prices = list(dict.fromkeys(_PRICE.findall(markdown)))[:10]
    ratings = _RATING.findall(markdown)

    data_tables = []

    if prices or ratings:
        rows = []
        if page_title:
            rows.append(["Title", page_title])
        if prices:
            rows.append(["Price", " / ".join(prices[:3])])
        if ratings:
            rows.append(["Rating", f"{ratings[0]} / 5 stars"])
        if rows:
            data_tables.append({"title": "Page Overview", "headers": ["Field", "Value"], "rows": rows})

    bullets = [_clean_md_link_text(b) for b in _BULLET.findall(markdown)]
    bullets = [b for b in bullets if len(b) > 10 and not b.startswith("http")]
    if bullets:
        data_tables.append({"title": "Key Points", "headers": ["Item"], "rows": [[b] for b in bullets[:25]]})

    for match in _TABLE.finditer(markdown):
        lines = match.group(0).strip().split('\n')
        if len(lines) >= 3:
            headers = [_sanitize_cell(h) for h in lines[0].split('|') if h.strip()]
            rows = []
            for row_line in lines[2:]:
                cells = [_sanitize_cell(_clean_md_link_text(c.strip())) for c in row_line.split('|') if c.strip()]
                if cells:
                    rows.append(cells)
            if headers and rows:
                data_tables.append({"title": "Table", "headers": headers, "rows": rows})

    if not data_tables and headings:
        data_tables.append({"title": "Page Sections", "headers": ["Section"], "rows": [[h] for h in headings[:20]]})

    err_note = f" | Gemini error: {error_msg}" if error_msg else " (Gemini unavailable — auto-parsed)"
    page_summary = f"{page_title}.{err_note}" if page_title else f"Page content extracted.{err_note}"

    return {
        "page_title": page_title,
        "page_summary": page_summary,
        "headings": headings,
        "paragraphs": paragraphs,
        "media": media,
        "links": links,
        "external_links": external_links,
        "data_tables": data_tables,
    }


# ──────────────────────────── Response Builder ─────────────────────

def _build_structured_result(structured: dict, firecrawl_links: list[dict] | None = None) -> StructuredResult:
    """Normalize a raw dict (from Gemini or fallback) into a validated StructuredResult."""

    def safe_str(v) -> str:
        return str(v) if not isinstance(v, str) else v

    def safe_rows(rows) -> list[list[str]]:
        result = []
        for row in rows:
            if isinstance(row, list):
                result.append([safe_str(cell) for cell in row])
        return result

    gemini_link_urls: set[str] = set()
    processed_links = []
    for l in structured.get("links", []):
        if isinstance(l, dict) and l.get("url") and l.get("text"):
            gemini_link_urls.add(l["url"])
            processed_links.append(LinkItem(text=safe_str(l["text"]), url=safe_str(l["url"])))

    # Merge Firecrawl structured links if Gemini missed them
    if firecrawl_links:
        for fc in firecrawl_links:
            fc_url = fc.get("url", "")
            fc_text = fc.get("text", "").strip()
            if fc_url and fc_text and fc_url not in gemini_link_urls:
                processed_links.append(LinkItem(text=fc_text, url=fc_url))

    return StructuredResult(
        page_title=safe_str(structured.get("page_title", "")),
        page_summary=safe_str(structured.get("page_summary", "No summary available.")),
        headings=[safe_str(h) for h in structured.get("headings", []) if h],
        paragraphs=[safe_str(p) for p in structured.get("paragraphs", []) if p],
        media=[
            MediaItem(**m) if isinstance(m, dict) else MediaItem(url=safe_str(m))
            for m in structured.get("media", [])
        ],
        links=processed_links,
        external_links=[safe_str(l) for l in structured.get("external_links", [])],
        data_tables=[
            DataTable(
                title=safe_str(t.get("title")) if isinstance(t, dict) else None,
                headers=[safe_str(h) for h in (t.get("headers", []) if isinstance(t, dict) else [])],
                rows=safe_rows(t.get("rows", []) if isinstance(t, dict) else []),
            )
            for t in structured.get("data_tables", [])
        ],
    )


# ──────────────────────────── Routes ──────────────────────────────


@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "aiwebscraper-smart-microservice",
        "version": "8.0.0",
    }


@app.post("/scrape-and-structure", response_model=ScrapeResponse)
async def scrape_and_structure(payload: ScrapeRequest):
    """
    Full pipeline:
    1. Rate-limit check (10/day per Gemini key)
    2. Firecrawl: URL → Markdown + links
    3. Pass 1: Classifier (5k chars → page_type)
    4. Pass 2: Gemini extractor (schema-aware prompt)
    5. Fallback regex parser if Gemini fails
    """
    url = str(payload.url)
    check_rate_limit(payload.user_gemini_key)
    logger.info(f"[v8] scrape-and-structure: {url}")

    # Step 1: Scrape
    raw_markdown, firecrawl_links = await fetch_markdown_via_firecrawl(url)
    logger.info(f"Firecrawl: {len(raw_markdown)} chars, {len(firecrawl_links)} links")

    # Step 2: Classify (Pass 1)
    page_type = await classify_page(raw_markdown, payload.user_gemini_key)

    # Step 3: Extract (Pass 2)
    structured, gemini_error = await structure_with_gemini(raw_markdown, payload.user_gemini_key, page_type)

    if structured is None:
        logger.warning(f"Gemini unavailable ({gemini_error}) — using fallback parser")
        structured = fallback_structure_from_markdown(raw_markdown, error_msg=gemini_error)

    return ScrapeResponse(
        url=url,
        page_type=page_type,
        structured_data=_build_structured_result(structured, firecrawl_links),
        raw_markdown=raw_markdown,
    )


@app.post("/search-and-structure", response_model=SearchResponse)
async def search_and_structure(payload: SearchRequest):
    """
    Search pipeline:
    1. Rate-limit check (10/day per Gemini key)
    2. Firecrawl search: query → top 3 result markdowns
    3. Concatenate markdowns
    4. Pass 1: Classify combined markdown
    5. Pass 2: Gemini extraction
    6. Fallback regex parser if Gemini fails
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    check_rate_limit(payload.user_gemini_key)
    logger.info(f"[v8] search-and-structure: '{query}'")

    # Step 1: Search
    markdowns, sources = await search_via_firecrawl(query)
    logger.info(f"Firecrawl search: {len(markdowns)} results for '{query}'")

    # Step 2: Combine results with source attribution headers
    combined_parts = []
    for i, (md, src) in enumerate(zip(markdowns, sources), 1):
        combined_parts.append(f"## Source {i}: {src}\n\n{md}")
    combined_markdown = "\n\n---\n\n".join(combined_parts)

    # Step 3: Classify
    page_type = await classify_page(combined_markdown, payload.user_gemini_key)

    # Step 4: Extract
    structured, gemini_error = await structure_with_gemini(combined_markdown, payload.user_gemini_key, page_type)

    if structured is None:
        logger.warning(f"Gemini unavailable ({gemini_error}) — using fallback parser")
        structured = fallback_structure_from_markdown(combined_markdown, error_msg=gemini_error)

    return SearchResponse(
        query=query,
        sources=sources,
        page_type=page_type,
        structured_data=_build_structured_result(structured),
        combined_markdown=combined_markdown,
    )
