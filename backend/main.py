"""
AIWebScraper Smart Microservice — v8.0
FastAPI backend: Aria Scraper + BYOK Gemini + Two-Pass Classification.

Changes in v8:
- Rate limiting: 10 extractions/day per Gemini key (in-memory, resets at UTC midnight)
- New /search-and-structure endpoint using Search Core /v1/search
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

PRIMARY_SCRAPER_API_KEY    = os.getenv("PRIMARY_SCRAPER_API_KEY")
PRIMARY_SCRAPER_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
PRIMARY_SCRAPER_SEARCH_URL = "https://api.firecrawl.dev/v1/search"

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
    description="Aria Scraper + BYOK Gemini: scrape or search any page, get structured JSON.",
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
    extraction_warning: str | None = None


class SearchResultItem(BaseModel):
    title: str
    description: str
    price: str | None = None
    image_url: str | None = None
    source_url: str

class SearchStructuredResponse(BaseModel):
    search_summary: str
    results: list[SearchResultItem]

class SearchResponse(BaseModel):
    query: str
    sources: list[str] = []
    page_type: str = "GENERAL"
    structured_data: SearchStructuredResponse
    combined_markdown: str


class ValidateKeyRequest(BaseModel):
    user_gemini_key: str


class ValidateKeyResponse(BaseModel):
    valid: bool
    error: str | None = None


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


# Block (multi-line) markup strippers for nav/header/footer/script/style sections
_STRIP_SCRIPT  = re.compile(r'(?is)<script[^>]*>.*?</script>')
_STRIP_STYLE   = re.compile(r'(?is)<style[^>]*>.*?</style>')
_STRIP_NAV     = re.compile(r'(?is)<nav[^>]*>.*?</nav>')
_STRIP_HEADER  = re.compile(r'(?is)<header[^>]*>.*?</header>')
_STRIP_FOOTER  = re.compile(r'(?is)<footer[^>]*>.*?</footer>')
# Strip bare URLs (not markdown image/link syntax) to reduce noise
_STRIP_RAW_URL = re.compile(r'(?<![\[!\(])https?://[^\s\)\]"]{30,}')


def _pre_clean_markdown(text: str) -> str:
    # Strip heavy HTML blocks first
    text = _STRIP_SCRIPT.sub('', text)
    text = _STRIP_STYLE.sub('', text)
    text = _STRIP_NAV.sub('', text)
    text = _STRIP_HEADER.sub('', text)
    text = _STRIP_FOOTER.sub('', text)
    text = _CLEAN_BR.sub("\n", text)
    text = _CLEAN_BOLD.sub("", text)
    text = _CLEAN_ITALIC.sub("", text)
    text = _CLEAN_SPAN.sub("", text)
    text = _CLEAN_ANCHOR.sub("", text)
    text = _CLEAN_TAGS.sub("", text)
    text = _CLEAN_NBSP.sub(" ", text)
    text = _CLEAN_AMP.sub("&", text)
    text = _CLEAN_ENTITIES.sub("", text)
    # Remove long standalone URLs that add noise without value
    text = _STRIP_RAW_URL.sub('', text)
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
            raise HTTPException(status_code=422, detail="Both Primary Scraper and Jina AI failed to load this page.")
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Failed to reach Jina AI fallback service.")


# ──────────────────────────── Primary Scraper Scrape ─────────────────────

async def fetch_markdown_via_primary_scraper(url: str) -> tuple[str, list[dict]]:
    """Returns (markdown, links_list)."""
    if not PRIMARY_SCRAPER_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfiguration: PRIMARY_SCRAPER_API_KEY is not set.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {PRIMARY_SCRAPER_API_KEY}",
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
            resp = await client.post(PRIMARY_SCRAPER_SCRAPE_URL, json=payload, headers=headers)
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
                raise HTTPException(status_code=status, detail="Access denied by the target website or Primary Scraper auth failed.")
            elif status == 402:
                raise HTTPException(status_code=502, detail="Primary Scraper API quota exceeded.")
            elif status in (408, 500, 502, 503):
                logger.warning(f"Primary Scraper returned {status} — falling back to Jina AI")
                fallback_md = await fetch_markdown_via_jina(url)
                return fallback_md, []
            else:
                raise HTTPException(
                    status_code=status,
                    detail=f"Primary Scraper error {status}: {error_body.get('error', e.response.text[:300])}",
                )
        except httpx.TimeoutException:
            logger.warning("Primary Scraper timed out — falling back to Jina AI")
            fallback_md = await fetch_markdown_via_jina(url)
            return fallback_md, []
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to reach Primary Scraper: {str(exc)}")

    data = resp.json()
    if not data.get("success"):
        error_msg = data.get("error", "")
        logger.warning(f"Primary Scraper success=false: {error_msg} — trying Jina fallback")
        fallback_md = await fetch_markdown_via_jina(url)
        return fallback_md, []

    page_data = data.get("data", {})
    markdown = page_data.get("markdown", "")
    links = page_data.get("links", [])

    if not markdown:
        raise HTTPException(status_code=422, detail="Primary Scraper returned no content. The page may require login or is empty.")

    return markdown, links


# ──────────────────────────── Primary Scraper Search ─────────────────────

async def search_via_primary_scraper(query: str) -> list[dict]:
    """
    Search using Primary Scraper /v1/search. Returns the raw results list from Primary Scraper.
    """
    if not PRIMARY_SCRAPER_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfiguration: PRIMARY_SCRAPER_API_KEY is not set.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {PRIMARY_SCRAPER_API_KEY}",
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
            resp = await client.post(PRIMARY_SCRAPER_SEARCH_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            raise HTTPException(
                status_code=status,
                detail=f"Primary Scraper search failed ({status}). Check your API key or query.",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to reach Primary Scraper search: {str(exc)}")

    data = resp.json()
    if not data.get("success"):
        raise HTTPException(status_code=502, detail=f"Primary Scraper search returned success=false: {data.get('error', '')}")

    results = data.get("data", [])
    if not results:
        raise HTTPException(status_code=422, detail=f"Primary Scraper search returned no results for: '{query}'")

    return results


# ──────────────────────────── Gemini System Prompt ─────────────────

GEMINI_SYSTEM_PROMPT = """\
You are an expert data extraction assistant. Extract ALL meaningful data from the provided Markdown content — do NOT classify the page as only one type. A page can contain articles AND products AND tables AND code simultaneously.

EXTRACTION STRATEGY — MANDATORY THREE-PHASE APPROACH:

PHASE 1 — SECTION CHUNKING (internal, do NOT output this):
Split the content into logical sections based on headings and topic changes.
Each section = one chunk. Do NOT merge sections. Do NOT split a section mid-content.
For each chunk, identify: section_title, type of content it contains (article text, item listings, table data, code blocks).
Ignore navigation menus, ads, footers, and repeated site-wide links.

PHASE 2 — MULTI-STRUCTURE EXTRACTION (internal, do NOT output this):
Process EVERY chunk and extract ALL structure types found within it:
a) ARTICLE CONTENT: headings, paragraphs — preserve ALL text, do NOT summarize or shorten.
b) REPEATED ITEMS: products, listings, cards — each item extracted individually, never merged.
c) TABLE DATA: headers and rows extracted completely, never truncated.
d) CODE BLOCKS: preserved as-is in paragraphs with a [Code] prefix.
e) LISTS: bullet/numbered lists preserved as individual paragraph items.

PHASE 3 — STRUCTURING (output this):
Combine ALL extracted data from EVERY chunk into a single JSON object with EXACTLY these fields:

{
  "page_title": "The main title or name of the page (from H1 or the first heading)",
  "page_summary": "A concise 2-3 sentence summary of what the page is about.",
  "headings": ["Every heading found on the page (H1, H2, H3, H4) as plain text strings, in document order"],
  "paragraphs": ["Every meaningful paragraph of body text, cleaned of markdown symbols. Each item is one paragraph. Include list items and code blocks here too."],
  "media": [
    {"url": "full image/video URL", "type": "image or video", "alt": "alt text or description"}
  ],
  "links": [
    {"text": "The visible link text — NEVER the raw URL as text", "url": "full https://... URL"}
  ],
  "external_links": ["array of unique external http/https URLs found in content"],
  "data_tables": [
    {
      "title": "Section/Table name — use the section_title from Phase 1 as context",
      "headers": ["Column1", "Column2"],
      "rows": [["value1", "value2"]]
    }
  ]
}

CRITICAL INSTRUCTIONS — violate none:

1. EXTRACT EVERYTHING: Do NOT classify the page as only one type. A Wikipedia page has BOTH article text AND tables AND links. An e-commerce page has BOTH product listings AND review text AND specifications tables. Process ALL of them.

2. BE EXHAUSTIVE: Do not summarize lists. Extract EVERY image, EVERY link, EVERY row, EVERY paragraph. Never output "..." or "etc". If a page has 50 paragraphs, return all 50.

3. DATA TABLES: Aggressively group repeating patterns (pricing, specs, feature lists, reviews, product grids, cast lists, FAQs, comparison tables) into data_tables. Use the section heading as the table title for context.

4. ALL row cell values MUST be plain text strings. Never put objects, arrays, or nulls inside a row cell. If a cell is empty, use "".

5. HEADINGS: Include every H1–H4 as plain text. Strip all # symbols.

6. PARAGRAPHS: Strip markdown symbols (**, *, _, #, >, -). Return clean readable sentences. Include list items and code block content.

7. MEDIA: Find every image (![alt](url) syntax AND raw image URLs). Find video embeds too.

8. NO MARKDOWN IN OUTPUT: All string values must be plain text.

9. Output ONLY raw, parseable JSON. No ```json fences. No commentary.

10. If a field has no data, return an empty array [].

PRIORITY RULES — extract in this order:
P1. Main content sections first (headings, core article text, paragraphs).
P2. Structured data next (repeated items, product listings, data tables).
P3. Media and links.
P4. Code blocks — only if they contain meaningful content (not boilerplate/config snippets).
If nearing output limits, sacrifice P4 before P3, P3 before P2. Never sacrifice P1 or P2.

QUALITY CONTROL:
Q1. Do NOT duplicate similar content. If the same text appears in both a heading and a paragraph, include it only once (in headings).
Q2. Do NOT extract navigation menus, site-wide footers, cookie banners, or repeated sidebar links.
Q3. Do NOT extract ad blocks or promotional banners unrelated to the page's main content.
Q4. Keep output clean and relevant — completeness means capturing all MEANINGFUL data, not all noise.

ZERO DATA LOSS RULES:
11. ONE-TO-ONE MAPPING: Each input item MUST produce exactly one output object. Do NOT skip, merge, or summarize. N items in → N items out.
12. HANDLE MISSING DATA: Use null or "" for missing fields — never drop an item.
13. CONSISTENCY: All objects in an array must have identical keys.
14. SECTION COMPLETENESS: Every section from Phase 1 MUST be represented. No section skipped or compressed.\
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

_UNIVERSAL_CAP = (
    "\n\nCRITICAL TRUNCATION PREVENTER: You are generating a structured JSON object. "
    "To prevent output truncation and reaching token limits, you MUST STRICTLY LIMIT the number of items extracted per array. "
    "Extract a MAXIMUM of 15 items per array (rows, links, paragraphs, media, external_links). "
    "Do NOT extract more than 15 items for ANY array, and limit data_tables to a maximum of 5 tables. "
    "Keep descriptions short and concise. Your output must natively finish and close all JSON brackets."
)


# ──────────────────────────── Pass 1: Classifier ───────────────────

def _classify_page_sync(preview: str, user_key: str) -> str:
    """Fast classifier — runs on first 5k chars, returns page_type string.
    Retries once on transient errors. Falls back to GENERAL on any failure."""
    import time
    client = genai.Client(api_key=user_key)
    prompt = _CLASSIFIER_PROMPT + preview

    max_attempts = 2
    models_to_try = ["gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"]

    for attempt in range(max_attempts):
        model = models_to_try[min(attempt, len(models_to_try) - 1)]
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_PageClassification,
                    temperature=0.0,
                    max_output_tokens=64,
                ),
            )

            # Null guard
            if response is None or not hasattr(response, 'text') or response.text is None:
                logger.warning(f"Classifier returned empty response (attempt {attempt+1}, model={model})")
                if attempt < max_attempts - 1:
                    time.sleep(1)
                    continue
                return "GENERAL"

            result = json.loads(response.text)
            page_type = result.get("page_type", "GENERAL").upper()
            return page_type if page_type in PAGE_TYPES else "GENERAL"

        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning(f"Classifier JSON parse error (attempt {attempt+1}): {exc}")
            return "GENERAL"

        except Exception as exc:
            error_str = str(exc).lower()
            is_transient = any(k in error_str for k in ("503", "unavailable", "429", "overloaded", "quota"))
            logger.warning(f"Classifier error (attempt {attempt+1}, model={model}): {exc}")
            if is_transient and attempt < max_attempts - 1:
                time.sleep(1.5)
                continue
            return "GENERAL"

    return "GENERAL"


_classifier_cache: dict[str, str] = {}

async def classify_page(markdown: str, user_key: str) -> str:
    """Async wrapper for the classifier. Defaults to GENERAL on any failure."""
    preview = _pre_clean_markdown(markdown)[:5000]
    
    preview_hash = hashlib.sha256(preview.encode('utf-8')).hexdigest()
    if preview_hash in _classifier_cache:
        logger.info(f"Classifier cache hit for {preview_hash[:8]}...")
        return _classifier_cache[preview_hash]

    loop = asyncio.get_event_loop()
    try:
        page_type = await loop.run_in_executor(_thread_pool, _classify_page_sync, preview, user_key)
        logger.info(f"Page classified as: {page_type}")
        
        _classifier_cache[preview_hash] = page_type
        if len(_classifier_cache) > 100:
            oldest_key = next(iter(_classifier_cache))
            del _classifier_cache[oldest_key]
            
        return page_type
    except Exception as exc:
        logger.warning(f"Classifier failed ({exc}) — defaulting to GENERAL")
        return "GENERAL"


SEARCH_SYSTEM_PROMPT = """You are an AI research assistant analyzing web search results. You MUST extract a structured list of the top items, products, or articles mentioned in the text. For every item, extract its title, a short description, the price (if applicable), the image URL, and the link to the item. Do not just summarize the page; you must populate the results array."""

def _call_gemini_sync(markdown: str, user_key: str, page_type: str = "GENERAL", is_search: bool = False, model: str = "gemini-3.1-flash", strict_count: int = 0) -> str:
    """
    Main extraction call — runs in a thread executor.
    Routes gemini-3.1-pro to raw HTTP v1 endpoint; all other models use the SDK.
    Strips and truncates content before sending.
    If strict_count > 0, injects an explicit item count requirement into the prompt.
    """
    cleaned = _pre_clean_markdown(markdown)
    truncated = _smart_truncate(cleaned, max_chars=10_000)

    before_len = len(markdown)
    after_len = len(truncated)
    logger.info(f"[{page_type}] Cleaned {before_len} → {after_len} chars before sending to Gemini ({model})")

    constraint_prompt = "ZERO LOSS MANDATE: Extract ALL structure types — articles, items, tables, code blocks — do NOT classify the page as only one type. Every distinct item, product, listing, or row MUST map to exactly one output entry. Preserve ALL paragraphs and list items without summarizing. Use null for missing fields instead of dropping items. Return a maximum of 20 items per data_table array. Be concise with field values. Do not include raw HTML. Keep string values under 200 characters. Your entire response must be valid complete JSON — never truncate."

    if strict_count > 0:
        constraint_prompt += (
            f" CRITICAL: The system detected EXACTLY {strict_count} distinct items in the input. "
            f"You previously returned fewer. You MUST now return EXACTLY {strict_count} items in data_tables rows. "
            f"Do NOT stop early. Do NOT merge items. Count your output before finishing."
        )

    if is_search:
        prompt = f"{SEARCH_SYSTEM_PROMPT}\n\nExtract ALL data from these search results:\n\n{truncated}\n\n{constraint_prompt}"
    else:
        prompt = f"{GEMINI_SYSTEM_PROMPT}{_UNIVERSAL_CAP}\n\nExtract ALL data from this web page markdown:\n\n{truncated}\n\n{constraint_prompt}"

    # ── Route: gemini-3.1-pro-preview → raw HTTP v1 endpoint ──
    if model == "gemini-3.1-pro-preview":
        return _call_gemini_v1_pro_sync(prompt, user_key)

    # ── Route: gemini-1.5-pro → also raw HTTP v1 (stable, non-SDK) ──
    if model == "gemini-1.5-pro":
        return _call_gemini_v1_http_sync(prompt, user_key, model)

    # ── Route: all other models → SDK ──
    return _call_gemini_sdk_sync(prompt, user_key, model, is_search)


def _call_gemini_v1_pro_sync(prompt: str, api_key: str) -> str:
    """
    Raw HTTP call to Gemini 3.1 Pro Preview via the v1 REST endpoint.
    Does NOT use the genai SDK — avoids v1beta conflicts.
    """
    return _call_gemini_v1_http_sync(prompt, api_key, "gemini-3.1-pro-preview")


def _call_gemini_v1_http_sync(prompt: str, api_key: str, model: str = "gemini-3.1-pro-preview") -> str:
    """
    Generic raw HTTP call to any Gemini model via the REST endpoint.
    Auto-selects v1beta for preview models, v1 for stable models.
    """
    api_version = "v1beta" if "preview" in model else "v1"
    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
        },
    }

    logger.info(f"[{model}] Sending request via raw HTTP {api_version} endpoint...")
    response = httpx.post(url, json=payload, timeout=120.0)

    if response.status_code == 401 or response.status_code == 403:
        raise ValueError(f"Invalid or unauthorized Gemini API key (HTTP {response.status_code})")
    if response.status_code == 404:
        raise ValueError(f"Model {model} not found (HTTP 404). May require API key upgrade or region change.")
    if response.status_code == 429:
        raise ValueError(f"Gemini quota exceeded (HTTP 429). Try again later.")
    if response.status_code >= 500:
        raise ValueError(f"Gemini server error (HTTP {response.status_code}). Service may be temporarily unavailable.")
    if response.status_code != 200:
        detail = response.text[:300] if response.text else "No details"
        raise ValueError(f"Gemini HTTP error {response.status_code}: {detail}")

    data = response.json()

    # Safety block check
    candidates = data.get("candidates", [])
    if not candidates:
        block_reason = data.get("promptFeedback", {}).get("blockReason", "UNKNOWN")
        raise ValueError(f"Gemini returned no candidates. Possibly blocked (reason: {block_reason}).")

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason", "")

    if finish_reason == "SAFETY":
        raise ValueError("Gemini blocked this content due to safety filters.")

    parts = candidate.get("content", {}).get("parts", [])
    if not parts or "text" not in parts[0]:
        raise ValueError(f"Gemini returned empty content (finishReason: {finish_reason}).")

    raw = parts[0]["text"]
    if not raw or not raw.strip():
        raise ValueError("Gemini returned empty text response.")

    logger.info(f"[{model}] HTTP response OK — {len(raw)} chars received")
    return raw


def _call_gemini_sdk_sync(prompt: str, user_key: str, model: str, is_search: bool = False) -> str:
    """
    SDK-based call for Flash and other non-Pro models.
    Uses genai.Client (instance-scoped, thread-safe).
    """
    client = genai.Client(api_key=user_key)
    schema = SearchStructuredResponse if is_search else StructuredResult

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
            max_output_tokens=8192,
            thinking_config={"include_thoughts": True}
        ),
    )

    # Null guard
    if response is None:
        raise ValueError("Gemini returned a None response object — possibly overloaded.")
    if not hasattr(response, 'text') or response.text is None:
        finish = getattr(getattr(response, 'candidates', [{}])[0] if response.candidates else {}, 'finish_reason', 'UNKNOWN')
        raise ValueError(f"Gemini returned empty response body (finish_reason={finish}) — possibly blocked or overloaded.")

    # Check for SAFETY block
    candidates = getattr(response, 'candidates', []) or []
    if candidates:
        finish_reason = str(getattr(candidates[0], 'finish_reason', '')).upper()
        if 'SAFETY' in finish_reason:
            raise ValueError("Gemini blocked this content due to safety filters.")
        if 'MAX_TOKENS' in finish_reason:
            logger.warning(f"Gemini hit MAX_TOKENS limit ({model}). Attempting JSON recovery from truncated output.")

    raw = response.text
    if not raw or not raw.strip():
        raise ValueError("Gemini returned empty string response.")

    return raw


# ──────────────────────────── Item Count Helpers ───────────────────

def _count_extracted_items(result: dict) -> int:
    """Count total structured items in a Gemini extraction result."""
    count = 0
    for table in result.get("data_tables", []):
        if isinstance(table, dict):
            count += len(table.get("rows", []))
    count += len(result.get("media", []))
    count += len(result.get("links", []))
    return count


def _count_input_sections(markdown: str) -> int:
    """Count distinct content sections in markdown by H2/H3 headings."""
    headings = re.findall(r'^#{2,3}\s+.+', markdown, re.MULTILINE)
    return len(headings)


def _count_output_sections(result: dict) -> int:
    """Count sections represented in the output (data_tables + headings array)."""
    table_count = len(result.get("data_tables", []))
    heading_count = len(result.get("headings", []))
    return max(table_count, heading_count)


def _count_expected_items(markdown: str) -> int:
    """Estimate expected item count from repeating patterns in the markdown."""
    import re
    # Count markdown list items (- item, * item, • item)
    bullets = len(re.findall(r'^[\-\*•]\s+.{10,}', markdown, re.MULTILINE))
    # Count markdown table rows (lines starting and ending with |)
    table_rows = len(re.findall(r'^\|.+\|$', markdown, re.MULTILINE))
    # Subtract header separator rows
    separators = len(re.findall(r'^\|[\s:\-|]+\|$', markdown, re.MULTILINE))
    table_rows = max(0, table_rows - separators * 2)  # header + separator
    # Count heading-delimited sections (## or ### followed by content)
    sections = len(re.findall(r'^#{2,4}\s+.+', markdown, re.MULTILINE))
    # Return the dominant pattern count (whichever is largest)
    return max(bullets, table_rows, sections)


async def structure_with_gemini(
    markdown: str, user_key: str, page_type: str = "GENERAL", is_search: bool = False
) -> tuple[dict | None, str | None]:
    """
    Run Gemini extraction in a thread pool.
    Returns (result_dict, error_message).
    3-tier fallback: gemini-3.1-pro (HTTP v1) → gemini-3.1-flash (SDK) → gemini-3.1-flash-lite-preview (SDK).
    JSON parsing wrapped in try/except with partial-JSON recovery.
    """
    max_retries = 5
    base_delay = 3
    last_error_msg: str | None = None
    raw_text: str = ""
    cleaned: str = ""

    # 3-tier model fallback chain (flash-first for reliability)
    _FALLBACK_CHAIN = ["gemini-3.1-flash", "gemini-3.1-flash-lite-preview", "gemini-1.5-pro"]
    current_model = _FALLBACK_CHAIN[0]
    fallback_index = 0

    for attempt in range(1, max_retries + 1):
        # Progressive fallback after consecutive failures
        if attempt == 3 and fallback_index < len(_FALLBACK_CHAIN) - 1:
            fallback_index += 1
            current_model = _FALLBACK_CHAIN[fallback_index]
            logger.warning(f"Switching to fallback model {current_model} after {attempt-1} failures.")

        try:
            loop = asyncio.get_event_loop()
            raw_text = await loop.run_in_executor(
                _thread_pool, _call_gemini_sync, markdown, user_key, page_type, is_search, current_model
            )

            # Strip accidental markdown fences
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned).strip()

            result = json.loads(cleaned)
            logger.info("Gemini extraction succeeded on attempt %d (page_type=%s, model=%s)", attempt, page_type, current_model)

            # ── External validation: system rejects mismatched output counts ──
            if not is_search:
                extracted_count = _count_extracted_items(result)
                expected_count = _count_expected_items(markdown)

                if expected_count > 0 and extracted_count < expected_count:
                    # System-enforced retry — model doesn't grade itself
                    for validation_attempt in range(1, 3):
                        logger.warning(
                            f"[EXTERNAL VALIDATOR] REJECTED: output={extracted_count} != expected≈{expected_count}. "
                            f"Re-extracting with strict_count={expected_count} (attempt {validation_attempt}/2)"
                        )
                        try:
                            retry_raw = await loop.run_in_executor(
                                _thread_pool, _call_gemini_sync,
                                markdown, user_key, page_type, is_search, current_model, expected_count
                            )
                            retry_cleaned = retry_raw.strip()
                            if retry_cleaned.startswith("```"):
                                retry_cleaned = re.sub(r"^```(?:json)?\s*", "", retry_cleaned)
                                retry_cleaned = re.sub(r"\s*```$", "", retry_cleaned).strip()
                            retry_result = json.loads(retry_cleaned)
                            retry_count = _count_extracted_items(retry_result)

                            # Always keep the result with the highest item count
                            if retry_count > extracted_count:
                                result = retry_result
                                extracted_count = retry_count
                                logger.info(f"[EXTERNAL VALIDATOR] Improved: {retry_count} items (was {extracted_count})")

                            # Accept if we hit or exceeded the target
                            if extracted_count >= expected_count:
                                logger.info(f"[EXTERNAL VALIDATOR] ACCEPTED: {extracted_count}/{expected_count} items")
                                break
                        except Exception as retry_exc:
                            logger.warning(f"[EXTERNAL VALIDATOR] Retry {validation_attempt} failed: {retry_exc}")

                    logger.info(f"Final item extraction: {extracted_count}/{expected_count} items (external validation complete)")

                # ── Section-level external check ──
                input_sections = _count_input_sections(markdown)
                output_sections = _count_output_sections(result)

                if input_sections > 0 and output_sections < input_sections:
                    logger.warning(
                        f"[SECTION VALIDATOR] Section mismatch: input={input_sections}, output={output_sections}. Retrying..."
                    )
                    try:
                        section_retry_raw = await loop.run_in_executor(
                            _thread_pool, _call_gemini_sync,
                            markdown, user_key, page_type, is_search, current_model, input_sections
                        )
                        section_cleaned = section_retry_raw.strip()
                        if section_cleaned.startswith("```"):
                            section_cleaned = re.sub(r"^```(?:json)?\s*", "", section_cleaned)
                            section_cleaned = re.sub(r"\s*```$", "", section_cleaned).strip()
                        section_result = json.loads(section_cleaned)
                        new_output_sections = _count_output_sections(section_result)

                        if new_output_sections > output_sections:
                            result = section_result
                            logger.info(f"[SECTION VALIDATOR] Improved: {new_output_sections} sections (was {output_sections})")
                        else:
                            logger.info(f"[SECTION VALIDATOR] No improvement: {new_output_sections} sections")
                    except Exception as sec_exc:
                        logger.warning(f"[SECTION VALIDATOR] Retry failed: {sec_exc}")
                else:
                    logger.info(f"[SECTION VALIDATOR] OK: {output_sections}/{input_sections} sections")

            return result, None

        except json.JSONDecodeError as exc:
            logger.warning(f"Gemini JSON parse failed (attempt {attempt}): {exc}")
            
            text_fix = cleaned
            
            if "Unterminated string" in str(exc) or "Expecting ',' delimiter" in str(exc) or "Expecting value" in str(exc):
                text_fix += '"'  # Add a quote in case we are cut off inside a string
                
            stripped = text_fix.lstrip()
            
            for _ in range(400): # Backtrack up to 400 chars
                try:
                    if stripped.startswith('{'):
                        ob = text_fix.count('{') - text_fix.count('}')
                        ok = text_fix.count('[') - text_fix.count(']')
                        candidate = text_fix + (']' * max(0, ok)) + ('}' * max(0, ob))
                    elif stripped.startswith('['):
                        ok = text_fix.count('[') - text_fix.count(']')
                        ob = text_fix.count('{') - text_fix.count('}')
                        candidate = text_fix + ('}' * max(0, ob)) + (']' * max(0, ok))
                    else:
                        candidate = text_fix

                    result = json.loads(candidate)
                    logger.info(f"Brute-force JSON recovery succeeded after backtracking {len(cleaned) - len(text_fix)} chars")
                    return result, None
                except json.JSONDecodeError:
                    if len(text_fix) > 10:
                        text_fix = text_fix[:-1] # chop one char and try again
                    else:
                        break
                        
            last_error_msg = f"Gemini returned malformed JSON: {exc}"
            break  # No point retrying completely bad JSON

        except Exception as exc:
            last_error_msg = str(exc)
            error_lower = last_error_msg.lower()
            logger.warning(f"Gemini attempt {attempt}/{max_retries} error ({current_model}): {exc}")

            # Auth errors — surface immediately
            if any(k in error_lower for k in ("api key", "api_key", "authenticate", "permission denied", "invalid", "unauthorized")):
                return None, f"Invalid or missing Gemini API key. Please update your key in settings. ({exc})"

            # Safety block
            if "safety" in error_lower or "blocked" in error_lower:
                return None, f"Gemini blocked this request due to safety filters. ({exc})"

            # Region/model-not-found errors — fallback to next model instead of hard failure
            if any(k in error_lower for k in ("user location", "not supported", "not found", "404")):
                if fallback_index < len(_FALLBACK_CHAIN) - 1:
                    fallback_index += 1
                    current_model = _FALLBACK_CHAIN[fallback_index]
                    logger.warning(f"Model not available — falling back to {current_model}")
                    continue
                return None, f"No available models for this API key/region. ({exc})"

            # Transient errors — retry with backoff and progressive fallback
            is_transient = any(k in error_lower for k in (
                "503", "unavailable", "429", "resource", "overloaded", "quota", "exhausted"
            ))
            if is_transient and attempt < max_retries:
                if fallback_index < len(_FALLBACK_CHAIN) - 1:
                    fallback_index += 1
                    current_model = _FALLBACK_CHAIN[fallback_index]
                    logger.warning(f"Transient error — falling back to {current_model}")
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Retrying in {delay}s (attempt {attempt+1}/{max_retries}, model={current_model})...")
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

def _build_structured_result(structured: dict, primary_scraper_links: list[dict] | None = None) -> StructuredResult:
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

    # Merge Primary Scraper structured links if Gemini missed them
    if primary_scraper_links:
        for fc in primary_scraper_links:
            if isinstance(fc, dict):
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


@app.post("/validate-key", response_model=ValidateKeyResponse)
async def validate_key(payload: ValidateKeyRequest):
    key = payload.user_gemini_key.strip()
    if not key:
        return ValidateKeyResponse(valid=False, error="API key is empty")
    try:
        # Use a raw HTTP request to completely bypass SDK quirks
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)
            
        if resp.status_code == 200:
            return ValidateKeyResponse(valid=True)
            
        err_data = resp.json()
        err_msg = err_data.get("error", {}).get("message", "Unknown error")
        
        if "API_KEY_INVALID" in str(err_data) or resp.status_code in (400, 403):
            return ValidateKeyResponse(valid=False, error="Invalid API key")
            
        return ValidateKeyResponse(valid=False, error=f"API Error: {err_msg[:100]}")
        
    except Exception as e:
        logger.warning(f"Key validation exception: {str(e)}")
        return ValidateKeyResponse(valid=False, error=f"Network Error: {str(e)[:100]}")


@app.get("/usage")
async def get_usage(gemini_key: str):
    today = str(date.today())
    kid = _key_id(gemini_key)
    entry = usage_tracker.get(kid)
    if not entry or entry["date"] != today:
        return {"used": 0, "limit": DAILY_LIMIT, "remaining": DAILY_LIMIT}
    used = entry["count"]
    return {
        "used": used,
        "limit": DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - used)
    }


@app.post("/scrape-and-structure", response_model=ScrapeResponse)
async def scrape_and_structure(payload: ScrapeRequest):
    """
    Full pipeline:
    1. Rate-limit check (10/day per Gemini key)
    2. Primary Scraper: URL → Markdown + links
    3. Pass 1: Classifier (5k chars → page_type)
    4. Pass 2: Gemini extractor (schema-aware prompt)
    5. Fallback regex parser if Gemini fails
    """
    url = str(payload.url)
    check_rate_limit(payload.user_gemini_key)
    logger.info(f"[v8] scrape-and-structure: {url}")

    # Step 1: Scrape
    raw_markdown, primary_scraper_links = await fetch_markdown_via_primary_scraper(url)
    logger.info(f"Primary Scraper: {len(raw_markdown)} chars, {len(primary_scraper_links)} links")

    # Step 2: Classify (Pass 1)
    page_type = await classify_page(raw_markdown, payload.user_gemini_key)

    # Step 3: Extract (Pass 2)
    structured, gemini_error = await structure_with_gemini(raw_markdown, payload.user_gemini_key, page_type)

    if structured is None:
        logger.warning(f"Gemini unavailable ({gemini_error}) — using fallback parser")
        structured = fallback_structure_from_markdown(raw_markdown, error_msg=gemini_error)
        extraction_warning = "AI extraction unavailable — basic parsing used. Results may be incomplete."
    else:
        extraction_warning = None

    return ScrapeResponse(
        url=url,
        page_type=page_type,
        structured_data=_build_structured_result(structured, primary_scraper_links),
        raw_markdown=raw_markdown,
        extraction_warning=extraction_warning,
    )


@app.post("/search-and-structure", response_model=SearchResponse)
async def search_and_structure(payload: SearchRequest):
    """
    Search pipeline (GEMINI BYPASSED):
    1. Primary Scraper search: query → raw organic search items
    2. Map metadata (title, description, ogImage) into SearchStructuredResponse natively.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    check_rate_limit(payload.user_gemini_key)

    logger.info(f"[v8] search-and-structure: '{query}' (Gemini bypassed)")

    # Step 1: Search via Primary Scraper
    results = await search_via_primary_scraper(query)
    logger.info(f"Primary Scraper search: {len(results)} results for '{query}'")

    # Step 2: Extract attributes directly into SearchResultItem without Gemini
    search_items = []
    sources = []
    
    for result in results:
        meta = result.get("metadata", {})
        title = meta.get("title") or "Untitled Result"
        description = meta.get("description") or result.get("markdown", "")[:200].strip() + "..."
        url = result.get("url") or meta.get("sourceURL", "")
        image = meta.get("ogImage")
        
        if url and (url not in sources):
            sources.append(url)
            search_items.append(SearchResultItem(
                title=title,
                description=description,
                price=None,
                image_url=image,
                source_url=url
            ))

    structured = SearchStructuredResponse(
        search_summary="Rich search items directly extracted from organic metadata via Primary Scraper web index.",
        results=search_items[:10]  # Cap visual results safely
    )

    return SearchResponse(
        query=query,
        sources=sources,
        page_type="GENERAL",
        structured_data=structured,
        combined_markdown="Gemini AI bypassed to prevent throttle errors. Raw metadata successfully loaded."
    )

