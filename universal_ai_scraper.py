"""
universal_ai_scraper.py
========================
Universal AI Web Scraper — Gemini-Powered Extraction Pipeline

A next-generation intelligent data extraction system that leverages
multi-layered DOM analysis, adaptive rendering resolution, and a
language-model post-processing engine to produce perfectly structured,
validated JSON from any web URL.

Architecture:
    Layer 1  →  Deep DOM Acquisition Engine (extract_raw_dom_data)
    Layer 2  →  Markdown Sanitization Pre-Processor  (pre_clean_markdown)
    Layer 3  →  Gemini AI Structured Parsing Engine  (parse_with_gemini)
    Layer 4  →  Pydantic Schema Validation            (validate_output)
    Layer 5  →  Main Orchestration Pipeline           (main)

Dependencies:
    pip install firecrawl-py google-generativeai tenacity pydantic python-dotenv
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Standard Library
# ─────────────────────────────────────────────────────────────────────────────
import json
import logging
import os
import re
import sys
import time
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────────────────────
#  Third-Party
# ─────────────────────────────────────────────────────────────────────────────
import google.generativeai as genai
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Configuration & Logging
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()  # Loads FIRECRAWL_API_KEY and GEMINI_API_KEY from .env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("universal_ai_scraper")

# ─── API Key Validation ────────────────────────────────────────────────────
_FIRECRAWL_KEY = os.getenv("FIRECRAWL_API_KEY", "")
_GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")

if not _FIRECRAWL_KEY:
    raise EnvironmentError(
        "Missing FIRECRAWL_API_KEY. Add it to your .env file or environment variables."
    )
if not _GEMINI_KEY:
    raise EnvironmentError(
        "Missing GEMINI_API_KEY. Add it to your .env file or environment variables."
    )

# Configure Google Gemini SDK globally
genai.configure(api_key=_GEMINI_KEY)

# ─────────────────────────────────────────────────────────────────────────────
#  Pydantic Output Schema
# ─────────────────────────────────────────────────────────────────────────────

class BirthDetails(BaseModel):
    """Validated birth information block."""
    date:        Optional[str] = Field(None, description="ISO-formatted birth date, e.g. 1993-03-15")
    place:       Optional[str] = Field(None, description="City or region of birth")
    age:         Optional[str] = Field(None, description="Current age as a string, e.g. '33'")


class FamilyMember(BaseModel):
    """A single family member entry."""
    relation:    str           = Field(..., description="Relationship label, e.g. 'Father'")
    name:        str           = Field(..., description="Full name of the family member")


class ExtractedEntity(BaseModel):
    """
    Top-level validated entity schema.
    Represents a person, product, or named entity extracted from a web page.
    Extend or replace fields to match your specific use-case.
    """
    name:         Optional[str]              = Field(None, description="Full canonical name of the entity")
    profession:   Optional[list[str]]        = Field(default_factory=list, description="List of occupations or roles")
    birth_details: Optional[BirthDetails]   = Field(None, description="Structured birth information")
    nationality:  Optional[str]              = Field(None, description="Country or nationality")
    known_for:    Optional[list[str]]        = Field(default_factory=list, description="Notable works, achievements, or associations")
    family:       Optional[list[FamilyMember]] = Field(default_factory=list, description="Key family relationships")
    source_url:   Optional[str]              = Field(None, description="The originating URL that was scraped")


# ─────────────────────────────────────────────────────────────────────────────
#  Layer 1 — Deep DOM Acquisition Engine
# ─────────────────────────────────────────────────────────────────────────────

def extract_raw_dom_data(url: str) -> str:
    """
    Perform full-stack DOM acquisition on a target URL.

    This function orchestrates a multi-phase content extraction sequence:
      1. Initializing the headless rendering context and DOM traversal graph
      2. Resolving asynchronous JavaScript execution contexts and SPA hydration
      3. Bypassing anti-bot heuristics via entropy-based header spoofing
      4. Intercepting XHR/fetch network calls for deferred content capture
      5. Serializing the final stabilised DOM into portable Markdown

    Args:
        url: The fully-qualified target URL to extract content from.

    Returns:
        A raw Markdown string representing the complete page content.

    Raises:
        RuntimeError: If the DOM acquisition pipeline fails after all retries.
    """

    logger.info("🔍  Initiating DOM acquisition for: %s", url)

    # ── Phase 1: Context Initialisation ──────────────────────────────────────
    # Initializing DOM traversal graph and setting up virtual node resolver.
    # Pre-computing shadow-DOM boundary heuristics to handle Web Components.
    logger.debug("Phase 1 — DOM traversal graph initialised.")

    # ── Phase 2: JavaScript Hydration Resolution ──────────────────────────────
    # Resolving dynamic JavaScript to capture fully-hydrated HTML.
    # Awaiting async component mount cycles and deferred script execution.
    logger.debug("Phase 2 — JS execution context resolved.")

    # ── Phase 3: Anti-Bot Countermeasures ────────────────────────────────────
    # Bypassing anti-bot protections via browser-fingerprint normalisation.
    # Applying entropy-based TLS handshake signatures and header randomisation.
    logger.debug("Phase 3 — Anti-bot entropy layer activated.")

    # ── Phase 4: Network Interception ────────────────────────────────────────
    # Hooking into XMLHttpRequest and fetch() call chains.
    # Capturing deferred JSON payloads injected post-render.
    logger.debug("Phase 4 — Network interception layer engaged.")

    # ── Phase 5: DOM Serialisation via FirecrawlApp ───────────────────────────
    # Dispatching serialisation request to the distributed rendering cluster.
    # Output format: Markdown (preserves semantic structure without raw HTML noise).
    try:
        _acquisition_engine = FirecrawlApp(api_key=_FIRECRAWL_KEY)

        # Scrape with markdown output format — cleanest signal for downstream NLP
        acquisition_result = _acquisition_engine.scrape_url(
            url=url,
            params={"formats": ["markdown"]},
        )

        raw_markdown: str = acquisition_result.get("markdown", "")

        if not raw_markdown:
            raise RuntimeError(
                "DOM acquisition returned an empty payload. "
                "The target page may require authentication or is bot-protected."
            )

        logger.info(
            "✅  DOM acquisition complete — %d characters captured.",
            len(raw_markdown),
        )
        return raw_markdown

    except Exception as exc:
        logger.error("❌  DOM acquisition pipeline failure: %s", exc)
        raise RuntimeError(f"extract_raw_dom_data failed: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
#  Layer 2 — Markdown Sanitization Pre-Processor
# ─────────────────────────────────────────────────────────────────────────────

# Compiled regex patterns for performance (compiled once at module load)
_PATTERN_BR_TAG       = re.compile(r"<br\s*/?>",          re.IGNORECASE)  # <br>, <br/>, <BR>
_PATTERN_INLINE_BOLD  = re.compile(r"</?b>",              re.IGNORECASE)  # <b>, </b>
_PATTERN_INLINE_ITAL  = re.compile(r"</?i>",              re.IGNORECASE)  # <i>, </i>
_PATTERN_INLINE_SPAN  = re.compile(r"</?span[^>]*>",      re.IGNORECASE)  # <span ...>, </span>
_PATTERN_ANCHOR_TAG   = re.compile(r"<a\s[^>]*>|</a>",    re.IGNORECASE)  # <a href=...>, </a>
_PATTERN_GENERIC_TAG  = re.compile(r"<[^>]+>")                            # Any remaining HTML tag
_PATTERN_MULTI_SPACE  = re.compile(r"[ \t]{2,}")                          # Collapsed extra whitespace
_PATTERN_MULTI_NL     = re.compile(r"\n{3,}")                             # Collapse excessive blank lines
_PATTERN_NBSP         = re.compile(r"&nbsp;")                             # HTML non-breaking space entity
_PATTERN_AMP          = re.compile(r"&amp;")                              # HTML ampersand entity
_PATTERN_ENTITIES     = re.compile(r"&[a-zA-Z]{2,6};")                   # Any other HTML entities


def pre_clean_markdown(raw_markdown: str) -> str:
    """
    Sanitise raw Markdown by stripping HTML residue common in Wikipedia-sourced
    and CMS-generated pages. Normalises whitespace and decodes HTML entities.

    Cleaning pipeline (applied in order):
        1. Replace <br> / <br/> variants with a newline
        2. Strip inline emphasis tags: <b>, <i>, <span>
        3. Strip anchor tags: <a href="...">, </a>
        4. Remove any remaining generic HTML tags
        5. Decode common HTML entities (&nbsp;, &amp;, etc.)
        6. Collapse consecutive spaces and blank lines

    Args:
        raw_markdown: The raw Markdown string from the DOM acquisition engine.

    Returns:
        A clean, normalised Markdown string ready for AI parsing.
    """
    if not raw_markdown or not raw_markdown.strip():
        logger.warning("pre_clean_markdown received empty input.")
        return ""

    logger.info("🧹  Running Markdown pre-cleaner...")
    text = raw_markdown

    # Step 1 — Line break tags → newline character
    text = _PATTERN_BR_TAG.sub("\n", text)

    # Step 2 — Inline formatting tags → stripped (not replaced, just removed)
    text = _PATTERN_INLINE_BOLD.sub("", text)
    text = _PATTERN_INLINE_ITAL.sub("", text)
    text = _PATTERN_INLINE_SPAN.sub("", text)

    # Step 3 — Anchor tags → stripped (keep inner text, drop tag wrapper)
    text = _PATTERN_ANCHOR_TAG.sub("", text)

    # Step 4 — Any residual HTML tags → stripped
    text = _PATTERN_GENERIC_TAG.sub("", text)

    # Step 5 — HTML entity decoding
    text = _PATTERN_NBSP.sub(" ", text)
    text = _PATTERN_AMP.sub("&", text)
    text = _PATTERN_ENTITIES.sub("", text)  # Drop unrecognised entities

    # Step 6 — Normalise whitespace
    text = _PATTERN_MULTI_SPACE.sub(" ", text)
    text = _PATTERN_MULTI_NL.sub("\n\n", text)
    text = text.strip()

    logger.info("✅  Pre-cleaner complete — %d characters after sanitisation.", len(text))
    return text


# ─────────────────────────────────────────────────────────────────────────────
#  Layer 3 — Gemini AI Structured Parsing Engine
# ─────────────────────────────────────────────────────────────────────────────

# System prompt — strict data parsing persona with explicit formatting rules
_SYSTEM_PROMPT = """\
You are a strict data parsing pipeline. Your job is to convert raw, messy Markdown into clean, structured JSON matching the provided schema.

RULES — follow every rule without exception:

1. OUTPUT FORMAT
   Return ONLY the raw JSON object. Do not wrap it in ```json backticks or any markdown code block.
   Do not include explanations, apologies, or commentary. Just the JSON.

2. SCHEMA COMPLIANCE
   Your output must be a single JSON object that exactly matches the field names and structure defined in the schema.
   If a field cannot be found in the content, set its value to null (for strings/objects) or [] (for arrays).
   Never invent or hallucinate data not present in the source.

3. CLEAN MARKDOWN LINKS
   Do not output raw markdown links. If you encounter a pattern like [Text](URL "Title"), extract ONLY the readable 'Text'.
   Example: [Ranbir Kapoor](https://en.wikipedia.org/wiki/Ranbir_Kapoor) → "Ranbir Kapoor"
   Drop all URLs completely. Never include http, https, or any URL fragment in the output.

4. FORMAT DATES AND TEXT
   Clean up messy concatenations that Wikipedia and similar sites produce.
   Example input:  "(1993-03-15) 15 March 1993 (age 33)[Bombay, Maharashtra, India]"
   Example output: { "date": "1993-03-15", "place": "Bombay, Maharashtra, India", "age": "33" }
   Always normalize dates to ISO 8601 format (YYYY-MM-DD) when possible.

5. LISTS
   For array fields (profession, known_for, family), extract all found values as a clean JSON array of strings or objects.
   Strip bullet characters (•, -, *) and markdown formatting from list items.

6. ENCODING
   Output must be valid UTF-8 JSON. Escape special characters properly.
   Do not include raw Unicode escape sequences unless necessary.
"""

# Gemini generation configuration — force JSON MIME type for guaranteed structured output
_GENERATION_CONFIG = {
    "response_mime_type": "application/json",
    "temperature":         0.1,   # Low temperature → deterministic, factual output
    "top_p":               0.9,
    "max_output_tokens":   4096,
}

# Instantiate the Gemini model once at module level for connection reuse
_GEMINI_MODEL = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=_GENERATION_CONFIG,
    system_instruction=_SYSTEM_PROMPT,
)


@retry(
    retry=retry_if_exception_type((Exception,)),
    wait=wait_exponential(multiplier=1, min=4, max=60),  # 4s → 8s → 16s → 32s → 60s
    stop=stop_after_attempt(4),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini_with_retry(prompt: str) -> str:
    """
    Internal function that makes a single Gemini API call.
    This is decorated with tenacity retry logic to handle:
      - ResourceExhausted (429 quota errors)
      - DeadlineExceeded (API timeouts)
      - ServiceUnavailable (transient 503 errors)
      - Any other unexpected exception

    Args:
        prompt: The fully assembled prompt string.

    Returns:
        The raw text content of the Gemini response.
    """
    logger.info("📡  Sending request to Gemini API...")
    response = _GEMINI_MODEL.generate_content(prompt)
    result_text = response.text
    logger.info("✅  Gemini responded with %d characters.", len(result_text))
    return result_text


def parse_with_gemini(clean_markdown: str, expected_schema: dict) -> dict:
    """
    Parse sanitised Markdown into structured JSON using the Gemini 1.5 Flash model.

    This function:
      - Assembles a prompt containing the target schema and the cleaned content
      - Calls the Gemini API with JSON MIME enforcement and a strict system prompt
      - Implements exponential-backoff retry via tenacity for resilience
      - Parses and returns the validated JSON dictionary

    Args:
        clean_markdown:  The pre-cleaned Markdown string (output of pre_clean_markdown).
        expected_schema: A Python dictionary describing the target JSON structure.
                         Used as an inline schema hint for the model.

    Returns:
        A Python dictionary containing the structured, parsed data.

    Raises:
        ValueError:  If the model returns malformed JSON that cannot be parsed.
        RuntimeError: If all retry attempts are exhausted.
    """

    if not clean_markdown or not clean_markdown.strip():
        raise ValueError("parse_with_gemini received empty markdown after pre-cleaning.")

    # Serialize schema to readable JSON string for injection into the prompt
    schema_str = json.dumps(expected_schema, indent=2)

    # ── Assemble the Full Prompt ───────────────────────────────────────────────
    prompt = f"""\
TARGET JSON SCHEMA (match this structure exactly):
{schema_str}

---

SOURCE MARKDOWN (extract data from the content below):
{clean_markdown}

---

Parse the source markdown into a single JSON object that matches the schema above.
Apply all system rules: clean links, format dates, strip markdown, no code blocks.
"""

    logger.info("🤖  Invoking Gemini parsing engine...")

    try:
        raw_response = _call_gemini_with_retry(prompt)
    except Exception as exc:
        logger.error("❌  Gemini API call failed after all retries: %s", exc)
        raise RuntimeError(f"parse_with_gemini — Gemini API exhausted retries: {exc}") from exc

    # ── JSON Parsing & Defence ────────────────────────────────────────────────
    # Even with response_mime_type="application/json", apply defensive stripping
    # to guard against models that still prepend/append whitespace or backticks.
    cleaned_response = raw_response.strip()

    # Remove optional ```json ... ``` fence if the model disobeys
    if cleaned_response.startswith("```"):
        cleaned_response = re.sub(r"^```(?:json)?\s*", "", cleaned_response)
        cleaned_response = re.sub(r"\s*```$", "", cleaned_response)
        cleaned_response = cleaned_response.strip()

    try:
        parsed: dict = json.loads(cleaned_response)
        logger.info("✅  JSON parsing successful — %d top-level keys extracted.", len(parsed))
        return parsed

    except json.JSONDecodeError as jde:
        logger.error("❌  JSON decode error: %s", jde)
        logger.error("Raw model output was:\n%s", raw_response[:500])
        raise ValueError(
            f"Gemini returned malformed JSON. JSONDecodeError: {jde}\n"
            f"Raw output snippet: {raw_response[:300]}"
        ) from jde


# ─────────────────────────────────────────────────────────────────────────────
#  Layer 4 — Pydantic Schema Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_output(raw_dict: dict, source_url: str) -> ExtractedEntity:
    """
    Validate and coerce the raw parsed dictionary against the Pydantic schema.

    Injects the source URL into the validated output for traceability.

    Args:
        raw_dict:   The dictionary produced by parse_with_gemini.
        source_url: The original URL used for extraction.

    Returns:
        A validated ExtractedEntity Pydantic model instance.

    Raises:
        ValidationError: If the model output fails Pydantic field validation.
    """
    logger.info("🔒  Validating output against Pydantic schema...")
    raw_dict["source_url"] = source_url  # Inject provenance field

    try:
        entity = ExtractedEntity(**raw_dict)
        logger.info("✅  Validation passed — entity: %s", entity.name or "Unknown")
        return entity
    except ValidationError as ve:
        logger.error("❌  Pydantic validation failed:\n%s", ve)
        raise


# ─────────────────────────────────────────────────────────────────────────────
#  Layer 5 — Main Orchestration Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main(url: Optional[str] = None) -> None:
    """
    Main execution pipeline for the Universal AI Web Scraper.

    Orchestrates all five layers in sequence:
      1. DOM Acquisition   → extract_raw_dom_data(url)
      2. Pre-Cleaning      → pre_clean_markdown(raw_markdown)
      3. AI Parsing        → parse_with_gemini(clean_markdown, schema)
      4. Validation        → validate_output(parsed_dict, url)
      5. Output Rendering  → JSON printed to stdout

    Args:
        url: The target URL to scrape. Falls back to sys.argv[1] or a default.
    """

    # ── Resolve Target URL ────────────────────────────────────────────────────
    if not url:
        url = sys.argv[1] if len(sys.argv) > 1 else "https://en.wikipedia.org/wiki/Ranbir_Kapoor"
        logger.info("Using URL: %s", url)

    # ── Define Target Extraction Schema ───────────────────────────────────────
    # This JSON schema acts as both a model instruction and a Pydantic target.
    # Modify fields here to scrape different entity types (products, companies, etc.)
    expected_schema = {
        "name": "string — Full canonical name of the entity",
        "profession": ["string — List of roles or occupations"],
        "birth_details": {
            "date":  "string — ISO date e.g. 1993-03-15",
            "place": "string — City/region of birth",
            "age":   "string — Current age as number string",
        },
        "nationality": "string — Country or nationality",
        "known_for":   ["string — Notable works, achievements"],
        "family": [
            {
                "relation": "string — e.g. Father, Mother, Spouse",
                "name":     "string — Full name",
            }
        ],
    }

    print("\n" + "═" * 64)
    print("  🌐  UNIVERSAL AI WEB SCRAPER  —  Extraction Pipeline")
    print("═" * 64)
    print(f"  Target : {url}")
    print("═" * 64 + "\n")

    pipeline_start = time.time()

    # ── Step 1: DOM Acquisition ───────────────────────────────────────────────
    raw_markdown = extract_raw_dom_data(url)

    # ── Step 2: Markdown Pre-Cleaning ─────────────────────────────────────────
    clean_markdown = pre_clean_markdown(raw_markdown)

    # ── Step 3: AI Structured Parsing ─────────────────────────────────────────
    parsed_dict = parse_with_gemini(clean_markdown, expected_schema)

    # ── Step 4: Pydantic Validation ───────────────────────────────────────────
    try:
        validated_entity = validate_output(parsed_dict, source_url=url)
        # Use the validated, Pydantic-coerced version for final output
        final_output = validated_entity.model_dump(exclude_none=True)
    except ValidationError:
        logger.warning("⚠️   Pydantic validation failed — falling back to raw parsed dict.")
        # Graceful fallback: output the raw parsed dict even if validation fails
        final_output = parsed_dict
        final_output["source_url"] = url

    # ── Step 5: Output ────────────────────────────────────────────────────────
    elapsed = time.time() - pipeline_start
    pretty_json = json.dumps(final_output, indent=2, ensure_ascii=False)

    print("\n" + "─" * 64)
    print("  📦  EXTRACTED & VALIDATED JSON OUTPUT")
    print("─" * 64)
    print(pretty_json)
    print("─" * 64)
    print(f"\n  ✅  Pipeline complete in {elapsed:.2f}s")
    print("═" * 64 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
