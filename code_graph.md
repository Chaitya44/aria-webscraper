# Aria WebScraper - Code Graph & Architecture Map

> **AI Instruction**: Read this file to instantly understand the structure, file paths, and logic flow of the Aria project. This minimizes tokens spent searching the filesystem.

## 1. High-Level Architecture
- **Stack**: Next.js (App Router, Tailwind, Firebase) + Python FastAPI + Google Gemini (BYOK).
- **Core Loop**: User enters URL/Prompt & API Key in React -> Next.js calls local FastAPI backend (`http://127.0.0.1:8000`) -> FastAPI fetches page data & asks Gemini to structure it -> Returns JSON -> React UI renders tables & metrics -> History saved to Firebase.

## 2. Directory & File Map

### `/backend` (Python FastAPI)
The brains of the extraction engine.
- `main.py`: **The God File for the backend.** 
  - **Endpoints**: `/scrape-and-structure` (Fetch + AI parse), `/search-and-structure` (Search engine + AI parse), `/validate-key` (Checks BYOK Gemini key validity using raw HTTP bypass), `/usage` (Checks rate limits).
  - **Logic**: Implements a "Two-Pass Architecture" using `gemini-1.5-flash`. Pass 1 classifies the page type (Article, E-Commerce, etc.). Pass 2 extracts structured JSON data based on that type. Rate limiting is kept in-memory.
- `requirements.txt`: Dependencies (`fastapi`, `uvicorn`, `google-genai`, `httpx`, `pydantic`).

### `/frontend/nexus-scraper-ui` (Next.js)
The unified user interface.

**App Router (`/app`)**:
- `page.tsx`: Main entry. Renders the `NexusDashboard`.
- `login/page.tsx`: Firebase Auth login/signup screen.
- `globals.css`: Custom CSS, dark mode styles, animated orbs, glassmorphism UI variables.

**Components (`/components`)**:
- `NexusDashboard.tsx`: **The God File for the frontend.** 
  - Contains almost ALL client-side UI logic.
  - Manages input state (URL vs Search Mode).
  - Renders the "Extracting..." state, handles API calls to `127.0.0.1:8000`.
  - Maps `result.structured_data` into visual elements (Data Tables, Media, Links, Headings, Text).
  - Includes granular JSON/CSV/TXT export functions for each section.
- `Header.tsx`: The top navigation. Handles user profile dropdown, Theme toggle, and Firebase auth state.
- *(Note: `CommandCenter.tsx`, `DataView.tsx`, `LiveNeuralLog.tsx`, `InputModule.tsx` are legacy components from an older UI iteration).*

**Libraries (`/lib`)**:
- `firebase.ts`: Firebase configuration and initialization.
- `history.ts`: Database abstraction layer. Contains functions to save, load, delete, and clear user scraping history to/from Firebase Firestore (`firestoreSave`, `firestoreLoad`). Also tracks daily limits in DB.

### `/` (Root Directory)
- `universal_ai_scraper.py`: Legacy standalone Python CLI version of the scraper.
- `core_scraper.py`: Legacy Firecrawl wrapper.
- `aria_blackbook_diagrams/`: Folder containing Mermaid `.md` diagrams of the system architecture (Use Case, DFD, Class, Activity, State).

## 3. Data Flow / Object Signatures
- **User BYOK Auth**: The API Key is stored in `localStorage` (`aria_gemini_key`) and sent with *every* POST request to the backend in the JSON payload (`user_gemini_key: string`).
- **Structured Data Response**: Backend always returns `{"url": string, "page_type": string, "structured_data": {...}, "raw_markdown": string}`.
- **Firebase Documents**: Saved in the `users/{uid}/history` collection.

---
**End of Graph.**
