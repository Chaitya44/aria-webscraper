"""
AIWebScraper Smart Microservice Edition
FastAPI backend using Firecrawl for anti-bot Markdown extraction
and BYOK Google Gemini for intelligent JSON structuring.
"""

import os
import re
import json
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import httpx
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# ──────────────────────────── Config ───────────────────────────────

load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"

logger = logging.getLogger("aiwebscraper")
logging.basicConfig(level=logging.INFO)

_thread_pool = ThreadPoolExecutor(max_workers=4)

# ──────────────────────────── App Setup ────────────────────────────

app = FastAPI(
    title="AIWebScraper — Smart Microservice",
    description="Firecrawl + BYOK Gemini: scrape any page and get structured JSON.",
    version="5.0.0",
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
    type: str | None = None
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


# ──────────────────────────── Helpers ─────────────────────────────

def _is_amazon_url(url: str) -> bool:
    """Check if a URL is from Amazon."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        return "amazon." in host or host.endswith(".amazon.com")
    except Exception:
        return False


# ──────────────────────────── Jina AI Fallback ────────────────────

async def fetch_markdown_via_jina(url: str) -> str:
    """Free fallback using Jina AI Reader (r.jina.ai).
    No API key required. Different IP pool — bypasses sites that block Firecrawl."""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "text/markdown, text/plain, */*",
        "X-Return-Format": "markdown",
        "X-Timeout": "30",
        # Real browser UA so Jina's renderer also isn't blocked
        "X-With-Generated-Alt": "true",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Both Firecrawl and Jina AI failed to load this page. The site may be completely blocking external access.",
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=502,
                detail="Failed to reach Jina AI fallback service.",
            )


# ──────────────────────────── Extraction Step ─────────────────────

async def fetch_markdown_via_firecrawl(url: str) -> str:
    """Call Firecrawl to get clean Markdown from any URL.
    Optimized payload with JS wait, mobile fallback for Amazon, Jina fallback on failure."""

    if not FIRECRAWL_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: FIRECRAWL_API_KEY is not set.",
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
    }

    is_amazon = _is_amazon_url(url)

    # Optimized base payload
    payload: dict = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": False,       # get everything, Gemini will structure it
        "removeBase64Images": True,      # keep payload small
        "skipTlsVerification": True,     # handle govt sites with SSL issues
        "timeout": 90000,
        "waitFor": 5000,                 # wait 5s for JS-heavy pages to fully render
    }

    if is_amazon:
        # Mobile Amazon is lighter and less bot-protected
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
                raise HTTPException(
                    status_code=404,
                    detail="The target webpage could not be found (404). Please check the URL.",
                )
            elif status in (401, 403):
                raise HTTPException(
                    status_code=status,
                    detail="Access denied by the target website or Firecrawl auth failed.",
                )
            elif status == 402:
                raise HTTPException(
                    status_code=502,
                    detail="Firecrawl API quota exceeded. Please check your Firecrawl plan.",
                )
            elif status in (408, 500, 502, 503):
                logger.warning(f"Firecrawl returned {status} — falling back to Jina AI Reader")
                return await fetch_markdown_via_jina(url)
            else:
                raise HTTPException(
                    status_code=status,
                    detail=f"Firecrawl error {status}: {error_body.get('error', e.response.text[:300])}",
                )
        except httpx.TimeoutException:
            logger.warning("Firecrawl timed out — falling back to Jina AI Reader")
            return await fetch_markdown_via_jina(url)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach Firecrawl: {str(exc)}",
            )

    data = resp.json()

    if not data.get("success"):
        error_msg = data.get("error", "")
        # If Firecrawl marked it as failure, try Jina before giving up
        logger.warning(f"Firecrawl success=false: {error_msg} — trying Jina fallback")
        return await fetch_markdown_via_jina(url)

    markdown = data.get("data", {}).get("markdown", "")
    if not markdown:
        raise HTTPException(
            status_code=422,
            detail="Firecrawl returned no Markdown content for this URL. The page may require login or is empty.",
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
- ALL string values in rows arrays MUST be plain strings, never arrays or nested objects.
- Return ONLY the JSON object, no other text."""


def _call_gemini_sync(markdown: str, user_key: str):
    """Synchronous Gemini call — run this in a thread executor."""
    genai.configure(api_key=user_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    max_chars = 80_000
    if len(markdown) > max_chars:
        markdown = markdown[:max_chars] + "\n\n[Content truncated for processing]"

    prompt = f"{GEMINI_SYSTEM_PROMPT}\n\nHere is the Markdown content to analyze:\n\n{markdown}"
    response = model.generate_content(prompt)
    return response.text


async def structure_with_gemini(markdown: str, user_key: str) -> dict | None:
    """Run Gemini in a thread pool so it doesn't block the async event loop.
    Includes retry logic with exponential backoff for transient failures."""

    max_retries = 3
    base_delay = 2

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            loop = asyncio.get_event_loop()
            raw_text = await loop.run_in_executor(
                _thread_pool, _call_gemini_sync, markdown, user_key
            )
            result = json.loads(raw_text)
            return result

        except json.JSONDecodeError as exc:
            logger.warning(f"Gemini JSON parse failed (attempt {attempt}): {exc}")
            # Try to extract JSON from a partially-wrapped response
            try:
                import re as _re
                match = _re.search(r'\{.*\}', raw_text, _re.DOTALL)  # type: ignore
                if match:
                    return json.loads(match.group(0))
            except Exception:
                pass
            last_exception = exc
            break  # no point retrying bad JSON

        except Exception as exc:
            last_exception = exc
            error_msg = str(exc).lower()

            # Auth errors — don't retry
            if "api key" in error_msg or "authenticate" in error_msg or "permission" in error_msg or "api_key" in error_msg:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid Gemini API key. Please check your key in settings.",
                )

            # Quota / overload — retry with backoff
            if attempt < max_retries and (
                "503" in error_msg or "unavailable" in error_msg
                or "429" in error_msg or "resource" in error_msg
                or "overloaded" in error_msg or "quota" in error_msg
            ):
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Gemini attempt {attempt}/{max_retries} failed (transient). Retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue

            break

    logger.warning(f"Gemini failed after {max_retries} attempts: {last_exception}")
    return None


# ──────────────────────────── Fallback Parser ─────────────────────

def fallback_structure_from_markdown(markdown: str) -> dict:
    """Extract structured data from raw Markdown without AI.
    Product/e-commerce aware: extracts title, price, rating, features, specs."""

    # ── Images ──────────────────────────────────────────────────────
    image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    media = [
        {"url": m.group(2), "type": "image", "alt": m.group(1) or None}
        for m in image_pattern.finditer(markdown)
        if not m.group(2).endswith(('.svg', '.ico'))
    ][:20]  # cap at 20 images

    # ── Links ───────────────────────────────────────────────────────
    link_pattern = re.compile(r'(?<!!)\[([^\]]*)\]\((https?://[^)]+)\)')
    raw_url_pattern = re.compile(r'(?<!\()\bhttps?://[^\s)>\]"]+', re.IGNORECASE)
    link_urls = set(m.group(2) for m in link_pattern.finditer(markdown))
    raw_urls = set(raw_url_pattern.findall(markdown))
    image_urls = {m["url"] for m in media}
    external_links = sorted((link_urls | raw_urls) - image_urls)[:80]

    # ── Headings ────────────────────────────────────────────────────
    heading_pattern = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)
    headings = heading_pattern.findall(markdown)

    # ── Product-specific extraction ─────────────────────────────────
    data_tables = []

    # Price pattern: ₹, $, €, USD, INR followed by digits
    price_pattern = re.compile(r'[\u20b9$€£]\s?[\d,]+(?:\.\d{1,2})?|\b(?:INR|USD|EUR|GBP)\s?[\d,]+(?:\.\d{1,2})?', re.IGNORECASE)
    prices = list(dict.fromkeys(price_pattern.findall(markdown)))[:10]

    # Rating pattern: 4.5 out of 5, 4.5/5, 4.5 stars
    rating_pattern = re.compile(r'([\d.]+)\s*(?:out of 5|/5|stars?|\u2605)', re.IGNORECASE)
    ratings = rating_pattern.findall(markdown)

    # Review count: (1,234 ratings), 1,234 reviews
    review_pattern = re.compile(r'([\d,]+)\s*(?:ratings?|reviews?|customer reviews?)', re.IGNORECASE)
    reviews = review_pattern.findall(markdown)

    # Product title: usually the first H1 or large heading
    title = headings[0] if headings else ""

    # Build product info table if we found product signals
    if prices or ratings:
        product_rows = []
        if title:
            product_rows.append(["Product Title", title])
        if prices:
            product_rows.append(["Price", " / ".join(prices[:3])])
        if ratings:
            product_rows.append(["Rating", f"{ratings[0]} / 5 stars"])
        if reviews:
            product_rows.append(["Total Reviews", reviews[0]])
        if product_rows:
            data_tables.append({
                "title": "Product Overview",
                "headers": ["Field", "Value"],
                "rows": product_rows,
            })

    # Bullet feature lists (common on Amazon: • Feature, - Feature)
    bullet_pattern = re.compile(r'^[\-\*•]\s+(.{10,120})$', re.MULTILINE)
    bullets = bullet_pattern.findall(markdown)
    if bullets:
        data_tables.append({
            "title": "Product Features",
            "headers": ["Feature"],
            "rows": [[b.strip()] for b in bullets[:20]],
        })

    # Markdown tables (specs, comparison tables)
    table_pattern = re.compile(r'(\|.+\|\n\|[\s:|-]+\|\n(?:\|.+\|\n?)+)', re.MULTILINE)
    for match in table_pattern.finditer(markdown):
        lines = match.group(0).strip().split('\n')
        if len(lines) >= 3:
            headers = [h.strip() for h in lines[0].split('|') if h.strip()]
            rows = []
            for row_line in lines[2:]:
                cells = [c.strip() for c in row_line.split('|') if c.strip()]
                if cells:
                    rows.append(cells)
            if headers and rows:
                data_tables.append({"title": "Specifications", "headers": headers, "rows": rows})

    # Last resort: build sections table from headings
    if not data_tables and headings:
        data_tables.append({
            "title": "Page Sections",
            "headers": ["Section"],
            "rows": [[h] for h in headings[:20]],
        })

    # ── Summary ─────────────────────────────────────────────────────
    if title and prices:
        page_summary = f"{title}. Price: {', '.join(prices[:2])}. {'Rating: ' + ratings[0] + '/5. ' if ratings else ''}(Auto-parsed — Gemini unavailable.)"
    elif headings:
        page_summary = f"Page: {headings[0]}. Contains {len(headings)} sections, {len(media)} images, {len(external_links)} links. (Auto-parsed — Gemini unavailable.)"
    else:
        page_summary = "Page content extracted successfully. (Auto-parsed — Gemini unavailable.)"

    return {
        "page_summary": page_summary,
        "media": media,
        "external_links": external_links,
        "data_tables": data_tables,
    }


# ──────────────────────────── Routes ──────────────────────────────

@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "aiwebscraper-smart-microservice",
        "version": "5.0.0",
    }


@app.post("/scrape-and-structure", response_model=ScrapeResponse)
async def scrape_and_structure(payload: ScrapeRequest):
    """
    Two-step pipeline:
    1. Firecrawl: URL → clean Markdown (server-side API key, Amazon-aware)
    2. Gemini:    Markdown → structured JSON (user's BYOK key, runs in thread)
    """
    url = str(payload.url)
    logger.info(f"[v5] Starting scrape-and-structure for: {url}")

    # Step 1: Scrape via Firecrawl (Amazon-aware)
    raw_markdown = await fetch_markdown_via_firecrawl(url)
    logger.info(f"Firecrawl returned {len(raw_markdown)} chars of Markdown")

    # Step 2: Structure via Gemini (non-blocking thread executor + retry + fallback)
    structured = await structure_with_gemini(raw_markdown, payload.user_gemini_key)

    if structured is None:
        logger.warning("Gemini unavailable — using fallback regex parser")
        structured = fallback_structure_from_markdown(raw_markdown)

    logger.info("Structuring complete")

    def safe_rows(rows):
        """Ensure all row cells are strings, never nested arrays."""
        result = []
        for row in rows:
            if isinstance(row, list):
                result.append([str(cell) if not isinstance(cell, str) else cell for cell in row])
        return result

    structured_data = StructuredResult(
        page_summary=structured.get("page_summary", "No summary available."),
        media=[
            MediaItem(**m) if isinstance(m, dict) else MediaItem(url=str(m))
            for m in structured.get("media", [])
        ],
        external_links=[str(l) for l in structured.get("external_links", [])],
        data_tables=[
            DataTable(
                title=t.get("title") if isinstance(t, dict) else str(t),
                headers=[str(h) for h in (t.get("headers", []) if isinstance(t, dict) else [])],
                rows=safe_rows(t.get("rows", []) if isinstance(t, dict) else []),
            )
            for t in structured.get("data_tables", [])
        ],
    )

    return ScrapeResponse(
        url=url,
        structured_data=structured_data,
        raw_markdown=raw_markdown,
    )
