# NEXUS SCRAPER UI

A futuristic, AI-powered web scraper frontend built with Next.js, featuring a "hacker aesthetic" with dark mode glassmorphism and live terminal logs.

## 🚀 Getting Started

### Prerequisites

You need to have Node.js installed on your system. Download it from [nodejs.org](https://nodejs.org/).

### Installation

1. Navigate to the project directory:
```bash
cd nexus-scraper-ui
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## ✨ Features

- **Command Center**: Live status indicators showing API health
- **Neural Log Terminal**: Real-time log output with typing animations
- **Smart Configuration**: Toggle switches for scraper settings
- **Data Views**: Switch between JSON and table formats
- **Export Options**: Download results as CSV or JSON
- **Glassmorphism Design**: Modern frosted glass UI effects
- **Dark Theme**: "Deep Space" color scheme with electric accents

## 🎨 Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Animation**: Framer Motion
- **Icons**: Lucide React

## 📦 Project Structure

```
nexus-scraper-ui/
├── app/
│   ├── globals.css       # Global styles and fonts
│   ├── layout.tsx        # Root layout
│   └── page.tsx          # Main dashboard
├── components/
│   ├── CommandCenter.tsx # Header with status
│   ├── InputModule.tsx   # URL input & toggles
│   ├── LiveNeuralLog.tsx # Terminal log viewer
│   └── DataView.tsx      # Results display
└── tailwind.config.ts    # Custom design tokens
```

## 🔧 Backend Integration

This frontend is designed to work with a Python backend using DrissionPage and Google Gemini API. To integrate:

1. Create API endpoints in your Python backend (e.g., using FastAPI or Flask)
2. Replace the `simulateScraping` function in `app/page.tsx` with actual API calls
3. Update the TypeScript interfaces to match your backend response format

## 📝 Customization

- **Colors**: Edit `tailwind.config.ts` to change the color scheme
- **Fonts**: Modify font imports in `app/globals.css`
- **Animations**: Adjust timing in component files or Tailwind config

## 🌐 Production Build

```bash
npm run build
npm start
```

## 📄 License

MIT
