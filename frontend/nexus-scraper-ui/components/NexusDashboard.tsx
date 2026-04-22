"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Search, Download, AlertTriangle, Loader2,
    Database, Table2, Globe, Zap, Clock, Shield, Radar,
    ArrowRight, Trash2, ExternalLink, Key, Eye, EyeOff, Settings, XCircle
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
    saveHistory as firestoreSave,
    loadHistory as firestoreLoad,
    deleteHistoryEntry as firestoreDelete,
    clearHistory as firestoreClear,
    getDailyScrapeCount as getDbDailyCount,
    incrementDailyScrapeCount as incDbDailyCount
} from "@/lib/history";

// ── Types ────────────────────────────────────────────────────────────────────
interface MediaItem { url: string; type?: string; alt?: string; }
interface LinkItem { text: string; url: string; }
interface DataTable { title?: string; headers: string[]; rows: string[][]; }
interface StructuredData {
    page_title: string;
    page_summary: string;
    headings: string[];
    paragraphs: string[];
    media: MediaItem[];
    links: LinkItem[];
    external_links: string[];
    data_tables: DataTable[];
}
interface ScrapeResponse {
    url: string;
    page_type: string;
    structured_data: StructuredData;
    raw_markdown: string;
}
interface SearchResultItem {
    title: string;
    description: string;
    price?: string;
    image_url?: string;
    source_url: string;
}
interface SearchStructuredResponse {
    search_summary: string;
    results: SearchResultItem[];
}
interface SearchResponse {
    query: string;
    sources: string[];
    page_type: string;
    structured_data: SearchStructuredResponse;
    combined_markdown: string;
}
interface HistoryEntry {
    id: string;
    url: string;
    timestamp: string;
    entityCount: number;
    totalItems: number;
    result: ScrapeResponse | SearchResponse;
}

const HISTORY_KEY = "aria_history";
const MAX_HISTORY = 5;
const DAILY_LIMIT = 10;
const SCRAPE_COUNT_PREFIX = "aria_scrapes_";

// Daily limits are now securely tracked in Firebase via lib/history

// ── Feature SVG Illustrations ────────────────────────────────────────────────
function UniversalIllustration() {
    return (
        <svg viewBox="0 0 80 80" fill="none" className="w-16 h-16">
            <circle cx="40" cy="40" r="28" stroke="url(#g1)" strokeWidth="1.5" strokeDasharray="4 3" />
            <circle cx="40" cy="40" r="18" stroke="url(#g1)" strokeWidth="1.5" opacity="0.6" />
            <ellipse cx="40" cy="40" rx="28" ry="12" stroke="url(#g1)" strokeWidth="1" opacity="0.4" />
            <circle cx="40" cy="12" r="3" fill="#34d399" />
            <circle cx="62" cy="52" r="2.5" fill="#22d3ee" />
            <circle cx="18" cy="48" r="2" fill="#a78bfa" />
            <line x1="40" y1="15" x2="40" y2="40" stroke="#34d399" strokeWidth="0.8" opacity="0.4" />
            <line x1="40" y1="40" x2="60" y2="51" stroke="#22d3ee" strokeWidth="0.8" opacity="0.4" />
            <line x1="40" y1="40" x2="20" y2="47" stroke="#a78bfa" strokeWidth="0.8" opacity="0.4" />
            <circle cx="40" cy="40" r="4" fill="url(#g1)" />
            <defs><linearGradient id="g1" x1="12" y1="12" x2="68" y2="68"><stop stopColor="#34d399" /><stop offset="1" stopColor="#22d3ee" /></linearGradient></defs>
        </svg>
    );
}

function AIIllustration() {
    return (
        <svg viewBox="0 0 80 80" fill="none" className="w-16 h-16">
            {/* Neural network nodes */}
            {[[20, 22], [20, 40], [20, 58], [40, 28], [40, 52], [60, 32], [60, 48], [40, 40]].map(([cx, cy], i) => (
                <circle key={i} cx={cx} cy={cy} r={i === 7 ? 5 : 3} fill={i === 7 ? "url(#g2)" : "none"} stroke="url(#g2)" strokeWidth={i === 7 ? 0 : 1.2} opacity={i < 3 ? 0.5 : 0.8} />
            ))}
            {/* Connections */}
            {[[20, 22, 40, 28], [20, 22, 40, 40], [20, 40, 40, 28], [20, 40, 40, 52], [20, 40, 40, 40], [20, 58, 40, 52], [20, 58, 40, 40], [40, 28, 60, 32], [40, 28, 60, 48], [40, 40, 60, 32], [40, 40, 60, 48], [40, 52, 60, 32], [40, 52, 60, 48]].map(([x1, y1, x2, y2], i) => (
                <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="url(#g2)" strokeWidth="0.6" opacity="0.25" />
            ))}
            {/* Pulse rings */}
            <circle cx="40" cy="40" r="12" stroke="#a78bfa" strokeWidth="0.8" opacity="0.2" strokeDasharray="2 3" />
            <circle cx="40" cy="40" r="22" stroke="#a78bfa" strokeWidth="0.5" opacity="0.1" strokeDasharray="3 4" />
            <defs><linearGradient id="g2" x1="20" y1="20" x2="60" y2="60"><stop stopColor="#a78bfa" /><stop offset="1" stopColor="#c084fc" /></linearGradient></defs>
        </svg>
    );
}

function StealthIllustration() {
    return (
        <svg viewBox="0 0 80 80" fill="none" className="w-16 h-16">
            <rect x="18" y="24" width="44" height="32" rx="4" stroke="url(#g3)" strokeWidth="1.5" />
            <rect x="22" y="28" width="36" height="22" rx="2" stroke="url(#g3)" strokeWidth="0.8" opacity="0.3" />
            {/* Shield */}
            <path d="M40 34 L48 38 L48 46 C48 50 44 53 40 55 C36 53 32 50 32 46 L32 38 Z" stroke="url(#g3)" strokeWidth="1.5" fill="none" />
            <path d="M37 44 L39.5 46.5 L44 41" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            {/* Signal waves */}
            <path d="M54 30 C57 30 58 32 58 35" stroke="#f59e0b" strokeWidth="0.8" opacity="0.4" strokeLinecap="round" />
            <path d="M54 28 C59 28 61 32 61 37" stroke="#f59e0b" strokeWidth="0.6" opacity="0.25" strokeLinecap="round" />
            <defs><linearGradient id="g3" x1="18" y1="24" x2="62" y2="56"><stop stopColor="#f59e0b" /><stop offset="1" stopColor="#f97316" /></linearGradient></defs>
        </svg>
    );
}

function StructuredIllustration() {
    return (
        <svg viewBox="0 0 80 80" fill="none" className="w-16 h-16">
            {/* JSON brackets */}
            <path d="M24 25 L18 25 C16 25 15 26 15 28 L15 37 C15 39 14 40 12 40 C14 40 15 41 15 43 L15 52 C15 54 16 55 18 55 L24 55" stroke="url(#g4)" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M56 25 L62 25 C64 25 65 26 65 28 L65 37 C65 39 66 40 68 40 C66 40 65 41 65 43 L65 52 C65 54 64 55 62 55 L56 55" stroke="url(#g4)" strokeWidth="1.5" strokeLinecap="round" />
            {/* Data rows */}
            <rect x="28" y="32" width="24" height="4" rx="1" fill="#06b6d4" opacity="0.3" />
            <rect x="28" y="39" width="18" height="4" rx="1" fill="#06b6d4" opacity="0.2" />
            <rect x="28" y="46" width="21" height="4" rx="1" fill="#06b6d4" opacity="0.15" />
            {/* Key dots */}
            <circle cx="30" cy="34" r="1.5" fill="#22d3ee" />
            <circle cx="30" cy="41" r="1.5" fill="#22d3ee" opacity="0.7" />
            <circle cx="30" cy="48" r="1.5" fill="#22d3ee" opacity="0.5" />
            <defs><linearGradient id="g4" x1="12" y1="25" x2="68" y2="55"><stop stopColor="#06b6d4" /><stop offset="1" stopColor="#3b82f6" /></linearGradient></defs>
        </svg>
    );
}

const FEATURES = [
    { Illustration: UniversalIllustration, title: "Universal Extraction", desc: "Works on any webpage — e-commerce, news, social media, music platforms, dashboards, forums, wikis, and more. No hardcoded selectors needed." },
    { Illustration: AIIllustration, title: "Gemini 2.5 AI Engine", desc: "Google's latest AI model reads the page semantically, discovers the data schema, and structures everything automatically." },
    { Illustration: StealthIllustration, title: "Stealth Extraction Engine", desc: "Cloud-powered browser with built-in anti-bot bypass, JS rendering, and intelligent Markdown extraction. No local browser needed." },
    { Illustration: StructuredIllustration, title: "Schema-Perfect JSON", desc: "Every column aligned, every field typed. Null-safe output with instant CSV and JSON export. Ready for analysis." },
];

// ── Main Component ───────────────────────────────────────────────────────────
export default function NexusDashboard() {
    const { user } = useAuth();
    const [mode, setMode] = useState<"scrape" | "search">("scrape");
    const [url, setUrl] = useState("");
    const [searchQuery, setSearchQuery] = useState("");

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ScrapeResponse | SearchResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [elapsed, setElapsed] = useState(0);
    const [todayCount, setTodayCount] = useState(0);
    const [history, setHistory] = useState<HistoryEntry[]>([]);
    const [geminiKey, setGeminiKey] = useState("");
    const [keyLoaded, setKeyLoaded] = useState(false);
    const [showKey, setShowKey] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    // isCancelled: true only BEFORE the Firecrawl API call is made
    const isCancelledRef = useRef(false);
    const [canCancel, setCanCancel] = useState(false); // show cancel button only pre-Firecrawl
    const resultRef = useRef<HTMLDivElement>(null);
    const errorRef = useRef<HTMLDivElement>(null);
    const [resultKey, setResultKey] = useState(0); // increments on each new extraction result

    // Load history + API key on mount (and when user changes)
    useEffect(() => {
        const loadData = async () => {
            try {
                const savedKey = localStorage.getItem("aria_gemini_key");
                // Set key BEFORE keyLoaded so the modal doesn't flash open
                if (savedKey) {
                    setGeminiKey(savedKey);
                }

                if (user) {
                    const entries = await firestoreLoad(user.uid);
                    const count = await getDbDailyCount(user.uid);
                    setTodayCount(count);
                    setHistory(entries.map(e => ({
                        id: e.id || Date.now().toString(),
                        url: e.url,
                        timestamp: e.timestamp,
                        entityCount: Object.keys(e.data || {}).length,
                        totalItems: e.itemCount,
                        result: e.data?.structured_data
                            ? { url: e.url, page_type: "GENERAL", structured_data: (e.data as any).structured_data, raw_markdown: "" }
                            : { url: e.url, page_type: "GENERAL", structured_data: { page_summary: "", media: [], external_links: [], data_tables: [] }, raw_markdown: "" },
                    })));
                } else {
                    const saved = localStorage.getItem(HISTORY_KEY);
                    if (saved) setHistory(JSON.parse(saved));
                    const localKey = SCRAPE_COUNT_PREFIX + new Date().toISOString().slice(0, 10);
                    setTodayCount(parseInt(localStorage.getItem(localKey) || "0", 10));
                }
            } catch (err) {
                console.error('[History] Failed to load:', err);
            } finally {
                // Only mark loaded AFTER state is fully set
                setKeyLoaded(true);
            }
        };
        loadData();
    }, [user]);

    const saveLocalHistory = (entries: HistoryEntry[]) => {
        setHistory(entries);
        localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
    };

    const addLog = useCallback((msg: string) => {
        setLogs((prev) => [...prev.slice(-5), msg]);
    }, []);

    const cancelExtraction = () => {
        isCancelledRef.current = true;
        setCanCancel(false);
        setLoading(false);
        setError(null);
        if (timerRef.current) clearInterval(timerRef.current);
        setElapsed(0);
        setLogs(["Extraction cancelled."]);
        window.dispatchEvent(new CustomEvent('aria-scraping', { detail: { active: false } }));
    };

    const handleExtract = async () => {
        const inputStr = mode === "scrape" ? url : searchQuery;
        if (!inputStr.trim()) return;

        if (mode === "scrape") {
            // ── Security: URL Validation ─────────────────────────────
            const trimmed = inputStr.trim();
            try {
                const parsed = new URL(trimmed);
                if (!["http:", "https:"].includes(parsed.protocol)) {
                    setError("Only http:// and https:// URLs are allowed.");
                    return;
                }
                // Block internal/private addresses (SSRF protection)
                const host = parsed.hostname.toLowerCase();
                if (host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0" ||
                    host.startsWith("192.168.") || host.startsWith("10.") || host.startsWith("172.") ||
                    host.endsWith(".local") || host.endsWith(".internal")) {
                    setError("Internal/private network URLs are not allowed for security reasons.");
                    return;
                }
            } catch {
                setError("Please enter a valid URL (e.g. https://example.com)");
                return;
            }
        } else {
            if (inputStr.trim().length < 3) {
                setError("Please enter a longer search query.");
                return;
            }
        }

        // ── Daily Scrape Limit ────────────────────────────────────
        let currentCount = 0;
        try {
            if (user) {
                currentCount = await getDbDailyCount(user.uid);
                setTodayCount(currentCount);
            } else {
                const key = SCRAPE_COUNT_PREFIX + new Date().toISOString().slice(0, 10);
                currentCount = parseInt(localStorage.getItem(key) || "0", 10);
                setTodayCount(currentCount);
            }
        } catch {
            // If Firebase check fails, don't block the user — just proceed
            currentCount = 0;
        }

        if (currentCount >= DAILY_LIMIT) {
            setError(`Daily limit reached (${DAILY_LIMIT}/${DAILY_LIMIT}). Resets tomorrow.`);
            return;
        }

        // ── API Key Validation ────────────────────────────────────
        if (!geminiKey.trim()) {
            setError("Please enter your Gemini API key first. Click the ⚙ API Key button above to add it.");
            setShowSettings(true);  // Auto-expand the settings panel

            return;
        }

        setLoading(true);
        setResult(null);
        setError(null);
        setElapsed(0);
        isCancelledRef.current = false;
        setCanCancel(true); // show cancel button — we haven't called Firecrawl yet
        setLogs(["Connecting to Web Extraction Engine...", "Extracting page content..."]);

        // Lock navigation during scraping
        window.dispatchEvent(new CustomEvent('aria-scraping', { detail: { active: true } }));

        timerRef.current = setInterval(() => setElapsed((p) => p + 1), 1000);

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
            const endpoint = mode === "scrape" ? "/scrape-and-structure" : "/search-and-structure";
            const payload = mode === "scrape" 
                 ? { url: inputStr.trim(), user_gemini_key: geminiKey }
                 : { query: inputStr.trim(), user_gemini_key: geminiKey };

            // Check if user hit cancel before we even fire the API call
            if (isCancelledRef.current) return;

            setCanCancel(false); // Firecrawl request is now in-flight — can't cancel
            addLog("Firecrawl API called — fetching page...");

            const res = await fetch(`${API_URL}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
                if (res.status === 401) {
                    throw new Error(errData.detail || "Invalid Gemini API key. Please check your key and try again.");
                } else if (res.status === 404) {
                    throw new Error(errData.detail || "The target webpage could not be found (404). Please check the URL/query.");
                }
                throw new Error(errData.detail || `Server error: ${res.status}`);
            }

            addLog("Extraction complete. Gemini is structuring data...");
            const json: ScrapeResponse | SearchResponse = await res.json();
            if (timerRef.current) clearInterval(timerRef.current);
            setLoading(false);
            setCanCancel(false);
            setResult(json);
            setResultKey(k => k + 1); // trigger flash animation
            window.dispatchEvent(new CustomEvent('aria-scraping', { detail: { active: false } }));
            // Auto-scroll to results
            setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);

            // Compute summary counts
            let tableCount = 0;
            let totalItems = 0;
            let sdToSave: any = json.structured_data;

            if (mode === "search") {
                const searchSd = json.structured_data as SearchStructuredResponse;
                tableCount = searchSd.results?.length || 0;
                totalItems = tableCount;
            } else {
                const scrapeSd = json.structured_data as StructuredData;
                tableCount = scrapeSd.data_tables?.length || 0;
                totalItems = (scrapeSd.data_tables?.reduce((sum: number, t: any) => sum + (t.rows?.length || 0), 0) || 0) 
                             + (scrapeSd.media?.length || 0) 
                             + (scrapeSd.external_links?.length || 0);
            }

            // Save to history
            const displayUrl = mode === "scrape" ? inputStr.trim() : `🔍 ${inputStr.trim()}`;
            const entry: HistoryEntry = {
                id: Date.now().toString(),
                url: displayUrl,
                timestamp: new Date().toLocaleString(),
                entityCount: tableCount,
                totalItems: totalItems,
                result: json,
            };

            if (user) {
                await firestoreSave(user.uid, {
                    url: entry.url,
                    timestamp: entry.timestamp,
                    data: { structured_data: sdToSave } as any,
                    schema: {} as any,
                    itemCount: entry.totalItems,
                });
                const entries = await firestoreLoad(user.uid);
                setHistory(entries.map(e => ({
                    id: e.id || Date.now().toString(),
                    url: e.url,
                    timestamp: e.timestamp,
                    entityCount: Object.keys(e.data || {}).length,
                    totalItems: e.itemCount,
                    result: e.data?.structured_data ? { url: e.url, page_type: "GENERAL", structured_data: (e.data as any).structured_data, raw_markdown: "" } : { url: e.url, page_type: "GENERAL", structured_data: { page_summary: "", media: [], external_links: [], data_tables: [] }, raw_markdown: "" },
                })));
            } else {
                const updated = [...history, entry].slice(-MAX_HISTORY);
                saveLocalHistory(updated);
            }

            // Increment daily scrape counter
            if (user) {
                await incDbDailyCount(user.uid);
                setTodayCount(prev => prev + 1);
            } else {
                const key = SCRAPE_COUNT_PREFIX + new Date().toISOString().slice(0, 10);
                const current = parseInt(localStorage.getItem(key) || "0", 10);
                localStorage.setItem(key, String(current + 1));
                setTodayCount(current + 1);
            }

            addLog(`Done — ${tableCount} tables/items fetched`);
        } catch (e: any) {
            if (timerRef.current) clearInterval(timerRef.current);
            setLoading(false);
            setCanCancel(false);
            setError(e.message || "Connection failed");
            addLog(`Error: ${e.message}`);
            window.dispatchEvent(new CustomEvent('aria-scraping', { detail: { active: false } }));
            // Auto-scroll to error
            setTimeout(() => errorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
        }
    };

    const loadFromHistory = (entry: HistoryEntry) => {
        if (entry.url.startsWith("🔍 ")) {
            setMode("search");
            setSearchQuery(entry.url.slice(2));
        } else {
            setMode("scrape");
            setUrl(entry.url);
        }
        setResult(entry.result);
        setError(null);
        setLogs([`Loaded from history: ${entry.url}`]);
    };

    const deleteHistory = async (id: string) => {
        if (user) {
            await firestoreDelete(user.uid, id);
            const entries = await firestoreLoad(user.uid);
            setHistory(entries.map(e => ({
                id: e.id || Date.now().toString(),
                url: e.url,
                timestamp: e.timestamp,
                entityCount: Object.keys(e.data || {}).length,
                totalItems: e.itemCount,
                result: e.data?.structured_data
                    ? { url: e.url, page_type: "GENERAL", structured_data: (e.data as any).structured_data, raw_markdown: "" }
                    : { url: e.url, page_type: "GENERAL", structured_data: { page_summary: "", media: [], external_links: [], data_tables: [] }, raw_markdown: "" },
            })));
        } else {
            const updated = history.filter((h) => h.id !== id);
            saveLocalHistory(updated);
        }
    };

    const handleClearHistory = async () => {
        if (user) {
            await firestoreClear(user.uid);
            setHistory([]);
        } else {
            saveLocalHistory([]);
        }
    };

    const exportJSON = () => {
        if (!result) return;
        const blob = new Blob([JSON.stringify(result.structured_data, null, 2)], { type: "application/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `aria-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(a.href);
    };

    const exportCSV = (table: DataTable) => {
        if (!table.headers.length) return;
        const header = table.headers.join(",");
        const rows = table.rows.map((row) =>
            row.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")
        );
        const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${(table.title || "data").replace(/\s+/g, "_")}-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
    };

    return (
        <div className="min-h-screen relative">
            {/* ── MANDATORY GEMINI KEY OVERLAY ──────────────────────────── */}
            <AnimatePresence>
                {keyLoaded && !geminiKey.trim() && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xl"
                    >
                        <motion.div
                            initial={{ scale: 0.95, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            className="w-full max-w-md glass-card gradient-border rounded-3xl p-8 glow-emerald relative overflow-hidden"
                        >
                            {/* Decorative orbs */}
                            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/20 blur-3xl -translate-y-1/2 translate-x-1/3 rounded-full" />
                            <div className="absolute bottom-0 left-0 w-32 h-32 bg-cyan-500/20 blur-3xl translate-y-1/2 -translate-x-1/3 rounded-full" />

                            <div className="relative z-10 text-center mb-6">
                                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-xl shadow-emerald-500/25 mx-auto mb-4">
                                    <Key size={28} className="text-white" />
                                </div>
                                <h2 className="text-2xl font-black text-white tracking-tight mb-2">Welcome to Aria</h2>
                                <p className="text-gray-400 text-sm leading-relaxed">
                                    To use the extraction engine, please provide your Google Gemini API key. It is stored securely in your browser.
                                </p>
                            </div>

                            <div className="relative z-10 space-y-4">
                                <div className="relative group">
                                    <input
                                        type={showKey ? "text" : "password"}
                                        id="gemini-modal-input"
                                        placeholder="AIzaSy..."
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") {
                                                const val = (e.target as HTMLInputElement).value;
                                                if (val.trim()) {
                                                    setGeminiKey(val.trim());
                                                    localStorage.setItem("aria_gemini_key", val.trim());
                                                }
                                            }
                                        }}
                                        className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl py-3.5 pl-4 pr-12 text-white font-mono text-sm focus:outline-none focus:border-emerald-500/50 transition-all font-medium placeholder:text-gray-600 focus:shadow-[0_0_20px_rgba(16,185,129,0.15)]"
                                    />
                                    <button
                                        onClick={() => setShowKey(!showKey)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-500 hover:text-emerald-400 transition-colors rounded-lg bg-white/[0.02] hover:bg-white/[0.04]"
                                    >
                                        {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                                    </button>
                                </div>

                                <button
                                    onClick={() => {
                                        const input = document.getElementById("gemini-modal-input") as HTMLInputElement;
                                        if (input && input.value.trim()) {
                                            setGeminiKey(input.value.trim());
                                            localStorage.setItem("aria_gemini_key", input.value.trim());
                                        }
                                    }}
                                    className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-emerald-500/25 transition-all text-sm tracking-wide"
                                >
                                    Save & Continue
                                </button>
                                
                                <p className="text-center mt-2">
                                    <a
                                        href="https://aistudio.google.com/apikey"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-[11px] text-emerald-500/80 hover:text-emerald-400 hover:underline transition-colors block p-2"
                                    >
                                        Don't have an API key? Get one for free →
                                    </a>
                                </p>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Lock overlay during scraping — prevents navigation but NOT cancel button */}
            {loading && !canCancel && (
                <div className="fixed inset-0 z-[99] bg-transparent cursor-wait" onClick={(e) => e.preventDefault()} />
            )}

            {/* Floating orbs */}
            <div className="orb" style={{ width: 400, height: 400, top: -100, left: -100, background: "rgba(16, 185, 129, 0.5)" }} />
            <div className="orb" style={{ width: 350, height: 350, bottom: -50, right: -50, background: "rgba(6, 182, 212, 0.4)", animationDelay: "-5s" }} />
            <div className="orb" style={{ width: 250, height: 250, top: "40%", right: "20%", background: "rgba(139, 92, 246, 0.3)", animationDelay: "-10s" }} />

            <div className="relative z-10 flex min-h-[calc(100vh-4rem)]" style={{ isolation: 'isolate' }}>

                {/* ── HISTORY SIDEBAR (left) ──────────────────────── */}
                {/* sticky so it stays fixed while main content scrolls */}
                <aside className="hidden lg:flex flex-col w-64 flex-shrink-0 border-r border-white/[0.04] history-sidebar sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto">
                    <div className="p-4 flex-1 overflow-y-auto">
                    <div className="flex items-center justify-between mb-4 px-1">
                        <div className="flex items-center space-x-2">
                            <Clock size={14} className="text-gray-500" />
                            <h2 className="text-xs font-bold text-white tracking-wide">History</h2>
                            <span className="text-[9px] bg-white/[0.06] px-1.5 py-0.5 rounded-full text-gray-500 font-medium">{history.length}/{MAX_HISTORY}</span>
                        </div>
                        {history.length > 0 && (
                            <button onClick={handleClearHistory} className="text-[10px] text-gray-600 hover:text-red-400 transition-colors">Clear</button>
                        )}
                    </div>
                    {history.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-emerald-500/10 flex items-center justify-center">
                                <Globe size={28} className="text-emerald-500/40" />
                            </div>
                            <p className="text-gray-500 text-xs font-semibold mb-1">No extractions yet</p>
                            <p className="text-gray-700 text-[10px] leading-relaxed px-4">Paste a URL and click Extract. Your last 5 results will appear here.</p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {history.map((entry) => (
                                <motion.div
                                    key={entry.id}
                                    layout
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="glass-card glass-card-hover rounded-xl px-3 py-3 cursor-pointer group"
                                    onClick={() => loadFromHistory(entry)}
                                >
                                    <div className="flex items-start space-x-2.5">
                                        <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center flex-shrink-0 mt-0.5 feature-icon-glow">
                                            <Globe size={12} className="text-emerald-500" />
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <p className="text-white text-[11px] font-semibold truncate" title={entry.url}>{entry.url}</p>
                                            <p className="text-gray-600 text-[10px] mt-0.5">
                                                {entry.totalItems > 0
                                                    ? <><span className="text-emerald-500/80">{entry.totalItems} items</span> · <span>{new Date(entry.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></>
                                                    : <><span className="text-gray-600">—</span> · <span>{new Date(entry.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></>
                                                }
                                            </p>
                                        </div>
                                        <button
                                            className="p-1 rounded-lg hover:bg-red-500/10 text-gray-700 hover:text-red-400 transition-all opacity-0 group-hover:opacity-100 flex-shrink-0"
                                            onClick={(e) => { e.stopPropagation(); deleteHistory(entry.id); }}
                                            title="Delete"
                                        >
                                            <Trash2 size={11} />
                                        </button>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}
                    </div>
                </aside>

                {/* ── MAIN CONTENT — left-offset so sidebar never hides it ── */}
                <div className="flex-1 min-w-0 px-4 md:px-8 py-6 md:py-10 overflow-x-hidden">
                    <div className="max-w-4xl mx-auto">

                    {/* ── HERO ──────────────────────────────────────────── */}
                    <motion.div initial={{ opacity: 0, y: -30 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-8 md:mb-12">
                        <div className="flex justify-center mb-6">
                            <img src="/aria-logo.png" alt="Aria Intelligence Logo" className="h-16 md:h-24 object-contain brightness-110 drop-shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:drop-shadow-[0_0_30px_rgba(16,185,129,0.5)] transition-all duration-300" />
                        </div>
                        <h1 className="text-4xl md:text-6xl lg:text-7xl font-black tracking-tight leading-[1.05] mb-3 md:mb-5">
                            <span className="text-transparent bg-clip-text bg-gradient-to-br from-emerald-300 via-teal-200 to-cyan-300">
                                Extract structured data
                            </span>
                            <br />
                            <span className="text-white/90 text-3xl md:text-5xl lg:text-6xl">from any website in seconds</span>
                        </h1>
                        <p className="text-gray-500 text-sm md:text-base max-w-xl mx-auto leading-relaxed font-light hidden md:block">
                            AI-powered extraction engine. Paste a URL — get clean tables, media, and links. Exports to JSON & CSV instantly.
                        </p>
                    </motion.div>

                    {/* ── FEATURE STRIP (compact icons) ────────────────────── */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 }}
                        className="flex flex-wrap items-center justify-center gap-4 md:gap-8 mb-8 md:mb-10"
                    >
                        {FEATURES.map((f, i) => (
                            <motion.div
                                key={f.title}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.15 + i * 0.05 }}
                                className="flex items-center space-x-2.5 group cursor-default"
                            >
                                <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center feature-icon-glow group-hover:scale-110 transition-transform duration-200">
                                    <f.Illustration />
                                </div>
                                <span className="text-gray-400 text-xs font-semibold tracking-tight group-hover:text-white transition-colors whitespace-nowrap">{f.title}</span>
                            </motion.div>
                        ))}
                    </motion.div>

                    {/* ── MAIN INPUT CARD ──────────────────────────────── */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.25 }}
                        className="glass-card gradient-border rounded-2xl overflow-hidden glow-emerald"
                    >
                        <div className="p-4 md:p-6 lg:p-10 space-y-4 md:space-y-6">
                            {/* API Key Settings */}
                            <div>
                                <button
                                    onClick={() => setShowSettings(!showSettings)}
                                    className="api-key-btn flex items-center space-x-2 text-xs font-semibold text-gray-400 hover:text-gray-200 transition-all py-2 mb-3"
                                >
                                    <Settings size={14} className={showSettings ? "text-emerald-400" : ""} />
                                    <span className="tracking-wide">API Key</span>
                                    {geminiKey ? (
                                        <span className="flex items-center space-x-1 ml-1">
                                            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
                                            <span className="text-emerald-400 text-[10px] font-bold">Connected</span>
                                        </span>
                                    ) : (
                                        <span className="text-red-400 text-[10px] font-bold ml-1 animate-pulse">● required</span>
                                    )}
                                </button>
                                <AnimatePresence>
                                    {showSettings && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: "auto", opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="overflow-hidden"
                                        >
                                            <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4 mb-4 space-y-3">
                                                <div className="flex items-center space-x-2">
                                                    <Key size={14} className="text-emerald-500 flex-shrink-0" />
                                                    <p className="text-gray-400 text-xs">
                                                        Enter your Gemini API key.{" "}
                                                        <a
                                                            href="https://aistudio.google.com/apikey"
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-emerald-500/70 hover:text-emerald-400 underline transition-colors"
                                                        >
                                                            Get a free key →
                                                        </a>
                                                    </p>
                                                </div>
                                                <div className="relative">
                                                    <input
                                                        type={showKey ? "text" : "password"}
                                                        value={geminiKey}
                                                        onChange={(e) => {
                                                            setGeminiKey(e.target.value);
                                                            localStorage.setItem("aria_gemini_key", e.target.value);
                                                        }}
                                                        placeholder="AIza..."
                                                        className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg py-2.5 pl-3 pr-10 text-white font-mono text-xs focus:outline-none focus:border-emerald-500/30 transition-all placeholder:text-gray-700"
                                                    />
                                                    <button
                                                        onClick={() => setShowKey(!showKey)}
                                                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400 transition-colors"
                                                    >
                                                        {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                                                    </button>
                                                </div>
                                                <p className="text-gray-600 text-[10px]">
                                                    🔒 Stored locally in your browser. Never sent to third parties.
                                                </p>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Input Area */}
                            <div className="space-y-4">
                                {/* Mode Toggle */}
                                <div className="flex space-x-2">
                                    <button
                                        onClick={() => setMode("scrape")}
                                        className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center space-x-2 border ${
                                            mode === "scrape" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.15)]" : "bg-white/[0.03] text-gray-400 border-transparent hover:bg-white/[0.06] hover:text-gray-300"
                                        }`}
                                    >
                                        <Globe size={16} />
                                        <span>Scrape URL</span>
                                    </button>
                                    <button
                                        onClick={() => setMode("search")}
                                        className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center space-x-2 border ${
                                            mode === "search" ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.15)]" : "bg-white/[0.03] text-gray-400 border-transparent hover:bg-white/[0.06] hover:text-gray-300"
                                        }`}
                                    >
                                        <Search size={16} />
                                        <span>Web Search</span>
                                    </button>
                                </div>

                                <div className="relative group">
                                    <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none">
                                        {mode === "scrape" ? (
                                            <Globe className="h-6 w-6 text-gray-600 group-focus-within:text-emerald-400 transition-colors duration-300" />
                                        ) : (
                                            <Search className="h-6 w-6 text-gray-600 group-focus-within:text-cyan-400 transition-colors duration-300" />
                                        )}
                                    </div>
                                    {mode === "scrape" ? (
                                        <input
                                            type="text"
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                            onKeyDown={(e) => e.key === "Enter" && !loading && handleExtract()}
                                            placeholder="https://example.com"
                                            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-2xl py-5 pl-14 pr-48 text-white font-mono text-base focus:outline-none focus:border-emerald-500/40 focus:bg-white/[0.05] focus:shadow-[0_0_30px_rgba(16,185,129,0.08)] transition-all duration-300 placeholder:text-gray-700"
                                        />
                                    ) : (
                                        <input
                                            type="text"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            onKeyDown={(e) => e.key === "Enter" && !loading && handleExtract()}
                                            placeholder="Search for anything (e.g. 'latest AI news')"
                                            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-2xl py-5 pl-14 pr-48 text-white font-mono text-base focus:outline-none focus:border-cyan-500/40 focus:bg-white/[0.05] focus:shadow-[0_0_30px_rgba(6,182,212,0.08)] transition-all duration-300 placeholder:text-gray-700"
                                        />
                                    )}
                                    <button
                                        onClick={handleExtract}
                                        disabled={loading || (mode === "scrape" ? !url.trim() : !searchQuery.trim())}
                                        className={`absolute right-2.5 top-2.5 bottom-2.5 px-10 rounded-xl font-bold text-base tracking-wide transition-all duration-200 flex items-center space-x-2.5 text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/50 hover:scale-[1.02] active:scale-[0.98] ${
                                            mode === "scrape" 
                                                ? "bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 border border-emerald-500/30" 
                                                : "bg-gradient-to-r from-cyan-600 to-blue-500 hover:from-cyan-500 hover:to-blue-400 border border-cyan-500/30"
                                        } disabled:from-gray-700 disabled:to-gray-700 disabled:opacity-40 disabled:border-transparent`}
                                    >
                                        {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
                                        <span>{loading ? "Extracting..." : "Extract"}</span>
                                    </button>
                                </div>
                            </div>


                            {/* Terminal */}
                            <div className="relative bg-[#08080d] rounded-2xl border border-white/[0.06] overflow-hidden shadow-2xl shadow-black/30">
                                <div className="h-9 border-b border-white/[0.06] flex items-center justify-between px-4">
                                    <div className="flex items-center space-x-1.5">
                                        <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
                                        <span className="ml-3 text-[10px] text-gray-600 font-mono">aria_agent</span>
                                    </div>
                                    <span className="text-[9px] text-gray-700 font-mono">{todayCount}/{DAILY_LIMIT} extractions today</span>
                                </div>
                                <div className="p-4 h-40 font-mono text-xs text-gray-500 overflow-y-auto">
                                    {logs.length === 0 && !loading && (
                                        <div className="flex items-start mb-1">
                                            <span className="text-emerald-600 mr-2 flex-shrink-0">$</span>
                                            <span className="text-gray-600">Awaiting input...</span>
                                            <span className="terminal-cursor" />
                                        </div>
                                    )}
                                    {logs.map((log, i) => (
                                        <motion.div key={`${i}-${log}`} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="mb-1 flex items-start">
                                            <span className="text-emerald-600 mr-2 flex-shrink-0">$</span>
                                            <span className="text-gray-400">{log}</span>
                                        </motion.div>
                                    ))}
                                </div>
                                {loading && (
                                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute bottom-3 right-4 flex items-baseline space-x-1">
                                        <span className="text-3xl font-bold tabular-nums text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.4)]">
                                            {elapsed}
                                        </span>
                                        <span className="text-emerald-600 text-xs font-medium">sec</span>
                                    </motion.div>
                                )}
                            </div>
                        </div>
                    </motion.div>

                    {/* ── ERROR ────────────────────────────────────────── */}
                    <AnimatePresence>
                        {error && (
                            <motion.div ref={errorRef as any} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                                className="mt-6 p-4 bg-red-500/5 border border-red-500/15 rounded-xl flex items-start space-x-3">
                                <AlertTriangle className="text-red-400 flex-shrink-0 mt-0.5" size={18} />
                                <div>
                                    <p className="text-red-400 font-semibold text-sm">Extraction Failed</p>
                                    <p className="text-red-400/60 text-xs mt-1">{error}</p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* ── HONEST STOPWATCH LOADER ─────────────────────── */}
                    <AnimatePresence>
                        {loading && (
                            <motion.div
                                initial={{ opacity: 0, y: 20, scale: 0.97 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: -10, scale: 0.97 }}
                                transition={{ type: "spring", stiffness: 200, damping: 24 }}
                                className="mt-8"
                            >
                                <div className="glass-card gradient-border rounded-2xl p-8 md:p-10 flex flex-col items-center text-center space-y-6 glow-emerald">
                                    {/* Pulsing Radar Icon */}
                                    <div className="relative">
                                        <div className="absolute inset-0 rounded-full bg-emerald-500/20 blur-xl animate-pulse" style={{ width: 72, height: 72, top: -4, left: -4 }} />
                                        <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500/15 to-cyan-500/15 border border-emerald-500/20 flex items-center justify-center">
                                            <Radar size={28} className="text-emerald-400 animate-pulse" />
                                        </div>
                                    </div>

                                    {/* Large Monospace Timer */}
                                    <div>
                                        <p className="text-gray-500 text-xs font-semibold uppercase tracking-widest mb-2">Time Elapsed</p>
                                        <p className="font-mono text-5xl md:text-6xl font-extrabold tabular-nums text-transparent bg-clip-text bg-gradient-to-r from-emerald-300 via-teal-200 to-cyan-300 drop-shadow-[0_0_16px_rgba(16,185,129,0.3)]">
                                            {elapsed}<span className="text-2xl md:text-3xl text-emerald-500/60 ml-1">s</span>
                                        </p>
                                    </div>

                                    {/* Phase-Aware Helper Text */}
                                    <p className="text-gray-400 text-sm max-w-md leading-relaxed font-light">
                                        {elapsed < 20
                                            ? "Bypassing security and analyzing DOM. Complex sites typically take 30\u201345 seconds."
                                            : "Scrape successful. Gemini AI is now structuring the raw data..."}
                                    </p>

                                    {/* Subtle animated progress bar (indeterminate) */}
                                    <div className="w-full max-w-xs h-1 rounded-full bg-white/[0.04] overflow-hidden">
                                        <motion.div
                                            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400"
                                            initial={{ x: "-100%" }}
                                            animate={{ x: "100%" }}
                                            transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
                                            style={{ width: "40%" }}
                                        />
                                    </div>

                                    {/* Cancel Button — only before Firecrawl fires */}
                                    <AnimatePresence>
                                        {canCancel && (
                                            <motion.button
                                                initial={{ opacity: 0, y: 8 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0, y: 8 }}
                                                onClick={cancelExtraction}
                                                className="relative z-[200] flex items-center space-x-2 px-6 py-2.5 rounded-xl border-2 border-red-500/50 text-red-400 hover:border-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all font-semibold text-sm cursor-pointer"
                                            >
                                                <XCircle size={16} />
                                                <span>Cancel Extraction</span>
                                            </motion.button>
                                        )}
                                    </AnimatePresence>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* ── RESULTS ──────────────────────────────────────── */}
                    <div key={resultKey} ref={resultRef} className={`mt-8 space-y-6 ${result ? 'results-flash' : ''}`}>
                        <AnimatePresence>
                            {result && typeof result.structured_data === 'object' && (
                                <>
                                    {/* Dual-Branch: Search vs Scrape Rendering */}
                                    {'search_summary' in result.structured_data ? (
                                        // ── SEARCH RENDERER ──
                                        <div className="space-y-6">
                                            {/* Search Overview Card */}
                                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                                className="glass-card rounded-xl px-6 py-4 space-y-3 border-cyan-500/10">
                                                <div className="flex flex-wrap items-center justify-between gap-3">
                                                    <div className="flex items-center space-x-3">
                                                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
                                                            <Search size={16} className="text-white" />
                                                        </div>
                                                        <div>
                                                            <p className="text-white font-semibold text-sm">Deep Web Search Complete</p>
                                                            <p className="text-gray-500 text-xs">
                                                                {(result.structured_data as SearchStructuredResponse).results?.length || 0} top results extracted · {elapsed}s
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                                <p className="text-cyan-100 text-sm leading-relaxed pt-2">
                                                    {(result.structured_data as SearchStructuredResponse).search_summary}
                                                </p>
                                            </motion.div>

                                            {/* Search Results Grid */}
                                            {(result.structured_data as SearchStructuredResponse).results?.length > 0 && (
                                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                                    {(result.structured_data as SearchStructuredResponse).results.map((item, idx) => (
                                                        <motion.div key={idx} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}
                                                            className="flex flex-col glass-card glass-card-hover rounded-xl overflow-hidden group">
                                                            
                                                            {/* Image Header */}
                                                            <div className="h-40 bg-[#08080d] relative overflow-hidden flex items-center justify-center border-b border-white/[0.04]">
                                                                {item.image_url ? (
                                                                    <img src={item.image_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                                                                ) : (
                                                                    <Globe size={40} className="text-gray-700 mx-auto opacity-30" />
                                                                )}
                                                                {item.price && item.price.toLowerCase() !== "none" && (
                                                                    <div className="absolute top-3 right-3 bg-black/80 backdrop-blur border border-white/10 px-3 py-1 rounded-full flex items-center shrink-0">
                                                                        <span className="text-emerald-400 font-bold text-sm tracking-wide">{item.price}</span>
                                                                    </div>
                                                                )}
                                                            </div>

                                                            {/* Content Body */}
                                                            <div className="p-5 flex-1 flex flex-col">
                                                                <h3 className="text-white font-bold text-base leading-snug mb-2 line-clamp-2 group-hover:text-cyan-400 transition-colors">{item.title}</h3>
                                                                <p className="text-gray-400 text-xs leading-relaxed line-clamp-3 mb-4 flex-1">
                                                                    {item.description}
                                                                </p>
                                                                <a href={item.source_url} target="_blank" rel="noopener noreferrer"
                                                                    className="mt-auto w-full flex items-center justify-center space-x-2 bg-white/[0.03] hover:bg-cyan-500/10 border border-white/[0.08] hover:border-cyan-500/30 text-gray-300 hover:text-cyan-300 py-2.5 rounded-lg transition-all font-medium text-xs">
                                                                    <ExternalLink size={14} />
                                                                    <span>Visit Source</span>
                                                                </a>
                                                            </div>
                                                        </motion.div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        // ── SCRAPE RENDERER ──
                                        <div className="space-y-6">
                                            {/* Summary Card */}
                                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                                className="glass-card rounded-xl px-6 py-4 space-y-3">
                                                <div className="flex flex-wrap items-center justify-between gap-3">
                                                    <div className="flex items-center space-x-3">
                                                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
                                                            <Database size={16} className="text-white" />
                                                        </div>
                                                        <div>
                                                            <p className="text-white font-semibold text-sm">Extraction Complete</p>
                                                            <p className="text-gray-500 text-xs">
                                                                {(result.structured_data as StructuredData).data_tables?.length || 0} tables · {(result.structured_data as StructuredData).media?.length || 0} media · {(result.structured_data as StructuredData).external_links?.length || 0} links · {elapsed}s
                                                            </p>
                                                        </div>
                                                    </div>
                                                    <button onClick={exportJSON}
                                                        className="flex items-center space-x-2 text-xs bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-gray-300 hover:text-white px-4 py-2 rounded-lg transition-all font-medium">
                                                        <Download size={13} /><span>Export JSON</span>
                                                    </button>
                                                </div>
                                                {(result.structured_data as StructuredData).page_summary && (
                                                    <p className="text-gray-300 text-sm leading-relaxed border-t border-white/[0.06] pt-3">
                                                        {(result.structured_data as StructuredData).page_summary}
                                                    </p>
                                                )}
                                            </motion.div>

                                            {/* Data Tables */}
                                            {(result.structured_data as StructuredData).data_tables?.map((table, idx) => (
                                                <motion.div key={idx} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}>
                                                    <div className="flex items-center justify-between mb-3">
                                                        <div className="flex items-center space-x-2.5">
                                                            <Table2 className="text-emerald-500" size={15} />
                                                            <h2 className="text-sm font-bold text-white tracking-wide">{table.title || `Table ${idx + 1}`}</h2>
                                                            <span className="text-[10px] bg-white/[0.06] px-2 py-0.5 rounded-full text-gray-500 font-medium">
                                                                {table.rows?.length || 0} rows
                                                            </span>
                                                        </div>
                                                        {table.rows?.length > 0 && (
                                                            <button onClick={() => exportCSV(table)}
                                                                className="text-[11px] text-gray-500 hover:text-gray-300 bg-white/[0.03] hover:bg-white/[0.06] px-3 py-1.5 rounded-lg border border-white/[0.05] transition-all font-medium">
                                                                CSV ↓
                                                            </button>
                                                        )}
                                                    </div>
                                                    <div className="glass-card rounded-xl overflow-hidden">
                                                        <div className="overflow-x-auto">
                                                            <table className="nexus-table w-full text-left">
                                                                <thead>
                                                                    <tr>
                                                                        <th className="w-10 text-center">#</th>
                                                                        {table.headers?.map((h) => <th key={h}>{h}</th>)}
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {table.rows?.map((row, rIdx) => (
                                                                        <tr key={rIdx}>
                                                                            <td className="text-center text-gray-700 text-xs">{rIdx + 1}</td>
                                                                            {row.map((cell, cIdx) => <td key={cIdx}>{renderCell(cell)}</td>)}
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            ))}

                                            {/* Media */}
                                            {(result.structured_data as StructuredData).media?.length > 0 && (
                                                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                                                    <div className="flex items-center space-x-2.5 mb-3">
                                                        <Globe className="text-cyan-500" size={15} />
                                                        <h2 className="text-sm font-bold text-white tracking-wide">Media</h2>
                                                        <span className="text-[10px] bg-white/[0.06] px-2 py-0.5 rounded-full text-gray-500 font-medium">
                                                            {(result.structured_data as StructuredData).media.length}
                                                        </span>
                                                    </div>
                                                    <div className="glass-card rounded-xl p-4">
                                                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                                            {(result.structured_data as StructuredData).media.map((m, i) => (
                                                                <a key={i} href={m.url} target="_blank" rel="noopener noreferrer"
                                                                    className="block rounded-lg overflow-hidden border border-white/[0.06] hover:border-emerald-500/30 transition-all group">
                                                                    <div className="aspect-video bg-white/[0.02] flex items-center justify-center overflow-hidden">
                                                                        {m.type === "video" ? (
                                                                            <span className="text-gray-500 text-xs">🎬 Video</span>
                                                                        ) : (
                                                                            <img src={m.url} alt={m.alt || ""} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" loading="lazy" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                                                                        )}
                                                                    </div>
                                                                    {m.alt && <p className="text-[10px] text-gray-500 p-2 truncate">{m.alt}</p>}
                                                                </a>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            )}

                                    {/* External Links */}
                                    {(result.structured_data as StructuredData).external_links?.length > 0 && (
                                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                                            <div className="flex items-center space-x-2.5 mb-3">
                                                <ExternalLink className="text-purple-400" size={15} />
                                                <h2 className="text-sm font-bold text-white tracking-wide">External Links</h2>
                                                <span className="text-[10px] bg-white/[0.06] px-2 py-0.5 rounded-full text-gray-500 font-medium">
                                                    {(result.structured_data as StructuredData).external_links.length}
                                                </span>
                                            </div>
                                            <div className="glass-card rounded-xl p-4">
                                                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                                    {(result.structured_data as StructuredData).external_links.map((link, i) => (
                                                        <a key={i} href={link} target="_blank" rel="noopener noreferrer"
                                                            className="block text-cyan-400/80 hover:text-cyan-300 text-xs truncate transition-colors">
                                                            {link}
                                                        </a>
                                                    ))}
                                                </div>
                                            </div>
                                        </motion.div>
                                        )}

                                    {/* Named Links (text + URL) */}
                                    {(result.structured_data as StructuredData).links?.length > 0 && (
                                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                                            <div className="flex items-center space-x-2.5 mb-3">
                                                <ExternalLink className="text-emerald-400" size={15} />
                                                <h2 className="text-sm font-bold text-white tracking-wide">Page Links</h2>
                                                <span className="text-[10px] bg-white/[0.06] px-2 py-0.5 rounded-full text-gray-500 font-medium">
                                                    {(result.structured_data as StructuredData).links.length}
                                                </span>
                                            </div>
                                            <div className="glass-card rounded-xl overflow-hidden">
                                                <div className="overflow-x-auto max-h-64 overflow-y-auto">
                                                    <table className="nexus-table w-full text-left">
                                                        <thead>
                                                            <tr>
                                                                <th className="w-10 text-center">#</th>
                                                                <th>Link Text</th>
                                                                <th>URL</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {(result.structured_data as StructuredData).links.map((link, i) => (
                                                                <tr key={i}>
                                                                    <td className="text-center text-gray-700 text-xs">{i + 1}</td>
                                                                    <td className="text-gray-300 text-xs">{link.text}</td>
                                                                    <td>
                                                                        <a href={link.url} target="_blank" rel="noopener noreferrer"
                                                                            className="text-cyan-400/80 hover:text-cyan-300 text-xs truncate block max-w-xs transition-colors">
                                                                            {link.url.length > 50 ? link.url.slice(0, 47) + '…' : link.url}
                                                                        </a>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}

                                    {/* Page Headings */}
                                    {(result.structured_data as StructuredData).headings?.length > 0 && (
                                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                                            <div className="flex items-center space-x-2.5 mb-3">
                                                <Database className="text-violet-400" size={15} />
                                                <h2 className="text-sm font-bold text-white tracking-wide">Page Headings</h2>
                                                <span className="text-[10px] bg-white/[0.06] px-2 py-0.5 rounded-full text-gray-500 font-medium">
                                                    {(result.structured_data as StructuredData).headings.length}
                                                </span>
                                            </div>
                                            <div className="glass-card rounded-xl p-4">
                                                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                                    {(result.structured_data as StructuredData).headings.map((h, i) => (
                                                        <p key={i} className="text-gray-300 text-xs py-1 border-b border-white/[0.04] last:border-0">
                                                            <span className="text-violet-400/60 mr-2 font-mono text-[10px]">H{i === 0 ? '1' : '2+'}</span>
                                                            {h}
                                                        </p>
                                                    ))}
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}

                                    {/* Paragraphs / Body Text */}
                                    {(result.structured_data as StructuredData).paragraphs?.length > 0 && (
                                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                                            <div className="flex items-center space-x-2.5 mb-3">
                                                <Zap className="text-amber-400" size={15} />
                                                <h2 className="text-sm font-bold text-white tracking-wide">Body Text</h2>
                                                <span className="text-[10px] bg-white/[0.06] px-2 py-0.5 rounded-full text-gray-500 font-medium">
                                                    {(result.structured_data as StructuredData).paragraphs.length} paragraphs
                                                </span>
                                            </div>
                                            <div className="glass-card rounded-xl p-4 space-y-3 max-h-96 overflow-y-auto">
                                                {(result.structured_data as StructuredData).paragraphs.map((para, i) => (
                                                    <p key={i} className="text-gray-400 text-xs leading-relaxed border-l-2 border-white/[0.06] pl-3 hover:border-emerald-500/30 transition-colors">
                                                        {para}
                                                    </p>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </div>
                            )}
                        </>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* ── EMPTY STATE ──────────────────────────────────── */}
                    {!result && !loading && !error && history.length === 0 && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="text-center py-16">
                            <div className="relative w-20 h-20 mx-auto mb-6">
                                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 blur-xl" />
                                <div className="relative w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-white/[0.06] flex items-center justify-center">
                                    <Globe size={32} className="text-emerald-500/40" />
                                </div>
                            </div>
                            <h3 className="text-gray-300 text-xl font-bold mb-2">Ready when you are</h3>
                            <p className="text-gray-500 text-sm max-w-md mx-auto leading-relaxed">
                                Paste any URL above — Aria will visit the page, understand its content,
                                and return clean, structured data you can export instantly.
                            </p>
                            <div className="flex flex-wrap justify-center gap-2 mt-8">
                                {["E-commerce", "News", "Social Media", "Music", "Real Estate", "Any page"].map((t) => (
                                    <span key={t} className="text-xs bg-white/[0.03] border border-white/[0.05] text-gray-400 px-3 py-1.5 rounded-lg font-medium">{t}</span>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {/* ── STICKY PRIVACY FOOTER ─────────────────────────── */}
                    <div className="mt-16 pb-6">
                        <div className="privacy-bar rounded-xl px-5 py-3 flex items-center justify-center space-x-1 text-center">
                            <Shield size={12} className="text-gray-600 flex-shrink-0" />
                            <p className="text-gray-600 text-[11px] font-medium">
                                By using Aria, you agree to our{" "}
                                <a href="/terms" className="text-emerald-500/70 hover:text-emerald-400 underline transition-colors">Terms of Service</a>{" "}and{" "}
                                <a href="/privacy" className="text-emerald-500/70 hover:text-emerald-400 underline transition-colors">Privacy Policy</a>
                            </p>
                        </div>
                    </div>

                    </div>{/* end max-w-4xl wrapper */}
                </div>{/* end main content */}
            </div>{/* end flex */}
        </div>
    );
}

// ── Cell Renderer ────────────────────────────────────────────────────────────
function renderCell(val: any, type?: string): React.ReactNode {
    if (val === null || val === undefined) return <span className="text-gray-700">—</span>;
    const str = String(val);
    if (type === "url" || str.startsWith("http://") || str.startsWith("https://")) {
        return <a href={str} target="_blank" rel="noopener noreferrer" className="text-cyan-400/80 hover:text-cyan-300 transition-colors" title={str}>{str.length > 40 ? str.slice(0, 37) + "…" : str}</a>;
    }
    if (type === "number" || (typeof val === "number" && !isNaN(val))) return <span className="tabular-nums text-gray-300">{val}</span>;
    if (type === "boolean" || typeof val === "boolean") return val ? <span className="text-emerald-400">✓</span> : <span className="text-gray-700">✗</span>;
    return str.length > 80 ? str.slice(0, 77) + "…" : str;
}
