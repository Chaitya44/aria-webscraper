# ✨ Aria — AI Web Data Extractor

Extract structured data from **any website** in seconds. Paste a URL, let Gemini AI read the page, and get clean tables, media, and links — exported as JSON or CSV.

![Aria Screenshot](https://img.shields.io/badge/Status-Live-brightgreen?style=for-the-badge) ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge) ![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js) ![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge&logo=fastapi)

---

## 🚀 Features

- **Universal Extraction** — Works on any URL: e-commerce, news, social media, forums, wikis
- **Gemini 2.5 AI Engine** — Google's AI reads pages semantically and structures everything automatically
- **Stealth Extraction** — Headless browser with anti-bot bypass and JavaScript rendering
- **Schema-Perfect Output** — Clean JSON & CSV with typed fields, null-safe values
- **10 Free Extractions/Day** — Per authenticated account
- **Regex Fallback** — If Gemini is unavailable, a built-in parser extracts images, links, tables, and headings
- **Firebase Auth** — Google & GitHub sign-in
- **Dark/Light Mode** — Premium UI with smooth theme transitions

---

## 📁 Project Structure

```
aria-webscraper/
├── backend/                 # FastAPI Python server
│   ├── main.py              # API routes + Gemini integration + fallback parser
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Container config for Render
├── frontend/
│   └── nexus-scraper-ui/    # Next.js 14 app
│       ├── app/             # Pages (login, dashboard, privacy, terms)
│       ├── components/      # NexusDashboard, Header, DataView, etc.
│       ├── contexts/        # AuthContext (Firebase)
│       ├── lib/             # Firebase config, Firestore history
│       └── .env.local.example
├── core_scraper.py          # Standalone scraper module (fallback)
├── .gitignore
└── README.md
```

---

## ⚡ Quick Start (Local Development)

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# Create .env with your Firecrawl API key
echo "FIRECRAWL_API_KEY=your-key" > .env

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend/nexus-scraper-ui
npm install

# Copy and fill in your Firebase credentials
cp .env.local.example .env.local
# Edit .env.local with your Firebase config

npm run dev
```

### 3. Open

Visit `http://localhost:3000` → Sign in → Enter your Gemini API key → Start extracting!

---

## 🔐 Environment Variables

### Backend (`backend/.env`)
| Variable | Description |
|----------|-------------|
| `FIRECRAWL_API_KEY` | Firecrawl API key for lightweight page extraction |

### Frontend (`frontend/nexus-scraper-ui/.env.local`)
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase messaging sender ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase app ID |
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://127.0.0.1:8000`) |

---

## 🌐 Free Deployment

| Service | Tier | What it hosts |
|---------|------|---------------|
| **Vercel** | Free Hobby | Frontend (Next.js) |
| **Render** | Free Web Service | Backend (FastAPI + Playwright) |
| **Firebase** | Free Spark | Authentication + Firestore |

See the detailed hosting guide in the repository wiki or the `HOSTING_GUIDE.md` file.

---

## 🔑 Getting a Gemini API Key

1. Visit [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Copy the key
4. Paste it into Aria when prompted on first login

The key is stored **locally in your browser** and never sent to third parties.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
