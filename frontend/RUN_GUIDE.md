# 🚀 Aria AI WebScraper — Complete Run Guide

---

## 1. Project Overview

**Aria** is an AI-powered web scraper with two parts:

| Part | Technology | What it does |
|------|-----------|--------------|
| **Backend** | Python (FastAPI) | Takes a URL, scrapes it via a Web Extraction Engine (cloud browser), then sends the raw content to Google Gemini AI to return clean, structured JSON |
| **Frontend** | Next.js (React) | A sleek dashboard where you paste any URL, see real-time progress, and get structured tables, media, and links — exportable as JSON/CSV |

**How it works:**
```
Frontend (localhost:3000)
    → sends URL to Backend (localhost:8000)
        → Backend calls Web Extraction Engine (URL → Markdown)
        → Backend calls Gemini AI (Markdown → structured JSON)
    → Frontend displays tables, media, links
```

> **Note:** The project uses **two separate servers** — you need **two terminal windows**.

---

## 2. Prerequisites

| Tool | Required Version | Status |
|------|-----------------|--------|
| **Node.js** | 18+ | ✅ Installed (v25.4.0) |
| **npm** | 8+ | ✅ Installed (11.7.0) |
| **Python** | 3.10+ | ✅ Installed (3.14.3 via `py` command) |
| **Backend venv** | — | ✅ Created at `backend/venv/` with all deps |
| **Frontend deps** | — | ✅ Installed at `nexus-scraper-ui/node_modules/` |

### API Keys You Need

| Key | Where to get it | Where it goes |
|-----|----------------|--------------|
| **Extraction Engine Key** | [firecrawl.dev](https://www.firecrawl.dev/) | `backend/.env` file (already configured) |
| **Gemini API Key** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Entered in the dashboard UI ⚙ button (stored in your browser) |

> **Important:** Firebase is **completely optional**. Without it, the app works in local mode — login is skipped and history is saved in your browser's localStorage.

---

## 3. Project Folder Structure

```
AI-WebScraper-main/
│
├── backend/                          ← Python FastAPI server
│   ├── .env                          ← Extraction engine API key lives here
│   ├── main.py                       ← The entire backend (1 file!)
│   ├── requirements.txt              ← Python dependencies
│   └── venv/                         ← Python virtual environment (pre-created)
│
├── frontend/
│   ├── RUN_GUIDE.md                  ← This file!
│   └── nexus-scraper-ui/             ← Next.js app
│       ├── app/                      ← Pages (dashboard, login, etc.)
│       ├── components/               ← UI components (NexusDashboard.tsx)
│       ├── lib/                      ← Firebase config & history helpers
│       ├── contexts/                 ← Auth context
│       ├── .env.local.example        ← Template for Firebase config (optional)
│       ├── package.json              ← Node dependencies
│       └── node_modules/             ← Installed packages (pre-installed)
```

---

## 4. Environment Setup

### 4a. Backend `.env` (Already configured ✅)

Your file at `backend/.env` already contains:
```env
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **Tip:** If this key expires, get a new free one at [firecrawl.dev/app/api-keys](https://www.firecrawl.dev/app/api-keys) and replace it in the `.env`.

### 4b. Frontend `.env.local` (Optional — for Firebase login only)

Only needed if you want Google/GitHub sign-in. **Skip this for local development.**

If you ever want to add it:
```powershell
# From: frontend\nexus-scraper-ui\
copy .env.local.example .env.local
# Then edit .env.local with your Firebase project credentials
```

---

## 5. Running the Project

### You need **TWO terminal windows** — one for the backend, one for the frontend.

---

### 🔧 Terminal 1 — Start the Backend

```powershell
# Step 1: Navigate to the backend folder
cd c:\Users\admin\Music\AI-WebScraper-main\backend

# Step 2: Activate the Python virtual environment
.\venv\Scripts\Activate.ps1

# Step 3: Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

> **Verify it works:** Open your browser and visit http://127.0.0.1:8000  
> You should see: `{"status":"ok","service":"aiwebscraper-smart-microservice","version":"4.0.0"}`

---

### 🎨 Terminal 2 — Start the Frontend

```powershell
# Step 1: Navigate to the frontend folder
cd c:\Users\admin\Music\AI-WebScraper-main\frontend\nexus-scraper-ui

# Step 2: Start the Next.js dev server
npm run dev
```

**Expected output:**
```
  ▲ Next.js 14.2.25
  - Local:        http://localhost:3000

 ✓ Ready in 2.1s
```

---

### 🎉 Open the App

Open your browser and go to: **http://localhost:3000**

---

## 6. How to Use the Dashboard

1. **Enter your Gemini API Key**
   - Click the **⚙ API Key** button in the input card
   - Paste your free key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - The indicator will turn green: `● Connected`

2. **Paste a URL**
   - Type or paste any webpage URL into the search bar
   - Example: `https://books.toscrape.com`

3. **Click "Extract"**
   - The Honest Stopwatch will appear showing elapsed time
   - Helper text changes after 20 seconds to indicate AI structuring phase
   - Complex sites typically take 30–45 seconds

4. **View & Export Results**
   - Browse extracted tables, media, and external links
   - Click **Export JSON** for the full dataset
   - Click **CSV ↓** on any individual table to export it

---

## 7. Database Setup

**No database setup required!** The app uses two storage modes automatically:

| Mode | When | Storage |
|------|------|---------|
| **Local mode** (default) | No Firebase configured | Browser's `localStorage` |
| **Cloud mode** | Firebase `.env.local` configured | Google Firestore |

---

## 8. Common Errors & Fixes

### ❌ `npm error ENOENT: could not read package.json`
**Cause:** Running `npm run dev` from the wrong folder.  
**Fix:** Make sure you're in the correct directory:
```powershell
cd c:\Users\admin\Music\AI-WebScraper-main\frontend\nexus-scraper-ui
npm run dev
```

### ❌ `python is not recognized`
**Cause:** Python isn't in your system PATH, but the `py` launcher works.  
**Fix:** Use the venv directly:
```powershell
cd c:\Users\admin\Music\AI-WebScraper-main\backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

### ❌ `EXTRACTOR_API_KEY is not set`
**Cause:** The `.env` file is missing or empty.  
**Fix:** Edit `backend/.env`:
```env
FIRECRAWL_API_KEY=fc-your-key-here
```

### ❌ `Invalid Gemini API key`
**Cause:** Wrong or expired key entered in the dashboard.  
**Fix:** Get a fresh free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and re-enter it in the ⚙ API Key panel.

### ❌ `Connection failed` or `Network Error`
**Cause:** Backend isn't running, or running on wrong port.  
**Fix:** Make sure Terminal 1 shows `Uvicorn running on http://0.0.0.0:8000`. The frontend expects the backend at `http://127.0.0.1:8000`.

### ❌ `Execution Policy` error when activating venv
**Cause:** PowerShell blocks scripts by default.  
**Fix:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
Then try activating again.

---

## 9. Quick-Start Cheat Sheet

Copy-paste these two blocks into **two separate terminals**:

**Terminal 1 (Backend):**
```powershell
cd c:\Users\admin\Music\AI-WebScraper-main\backend; .\venv\Scripts\Activate.ps1; uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd c:\Users\admin\Music\AI-WebScraper-main\frontend\nexus-scraper-ui; npm run dev
```

**Then open:** http://localhost:3000 🎉

---

## 10. Stopping the Servers

Press **`Ctrl + C`** in each terminal window to stop each server.

---

## 11. Conclusion

When both servers are running successfully, you should see:

- ✅ **Backend** at `http://127.0.0.1:8000` — returns `{"status": "ok"}`
- ✅ **Frontend** at `http://localhost:3000` — the Aria dashboard loads
- ✅ **Enter Gemini key** → paste a URL → click Extract → structured data appears
- ✅ **Export** results as JSON or CSV

> **Tip:** Bookmark this guide! Whenever you want to work on the project, just open two terminals and run the commands from Section 9.
