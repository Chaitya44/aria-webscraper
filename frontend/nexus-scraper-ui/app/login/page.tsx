"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Shield, Lock, Sparkles, Sun, Moon, Globe, Brain, Database } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { isConfigured } from "@/lib/firebase";
import { useEffect, useState } from "react";
import Link from "next/link";

const FEATURES = [
    { icon: Globe, title: "Any Website", desc: "E-commerce, news, social, forums — works everywhere without hardcoded selectors" },
    { icon: Brain, title: "AI-Powered", desc: "Gemini 2.5 reads the page semantically and structures everything automatically" },
    { icon: Database, title: "Clean Export", desc: "Schema-perfect JSON & CSV with null-safe, typed fields ready for analysis" },
    { icon: Shield, title: "Privacy First", desc: "All processing happens locally on your machine — zero data leaves your browser" },
];

export default function LoginPage() {
    const router = useRouter();
    const { user, signInWithGoogle, signInWithGitHub, loading: authContextLoading } = useAuth();
    const [theme, setTheme] = useState<"dark" | "light">("dark");
    const [acceptedTerms, setAcceptedTerms] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);
    const [authLoading, setAuthLoading] = useState(false);

    useEffect(() => {
        const saved = localStorage.getItem("aria_theme") as "dark" | "light" | null;
        if (saved) {
            setTheme(saved);
            document.documentElement.classList.toggle("light", saved === "light");
        }
    }, []);

    useEffect(() => {
        if (user) {
            console.log("[Auth] User authenticated, redirecting to dashboard", user.email);
            router.replace("/");
        }
    }, [user, router]);

    const toggleTheme = () => {
        const next = theme === "dark" ? "light" : "dark";
        setTheme(next);
        localStorage.setItem("aria_theme", next);
        document.documentElement.classList.toggle("light", next === "light");
    };

    const handleGoogle = async () => {
        if (!acceptedTerms) return;
        if (!isConfigured) {
            alert("Firebase is not configured.\n\nTo enable sign-in, create a Firebase project and add your credentials to:\nfrontend/nexus-scraper-ui/.env.local\n\nSee .env.local.example for the required variables.");
            return;
        }
        setAuthError(null);
        setAuthLoading(true);
        try {
            await signInWithGoogle();
            console.log("[Auth] Google sign-in succeeded");
            router.replace("/");
        } catch (e: any) {
            console.error("[Auth] Google sign-in failed:", e.message);
            const msg = e.code === 'auth/popup-closed-by-user'
                ? "Sign-in popup was closed. Please try again."
                : e.code === 'auth/popup-blocked'
                ? "Popup was blocked by your browser. Please allow popups and try again."
                : e.message || "Sign-in failed. Please try again.";
            setAuthError(msg);
        } finally {
            setAuthLoading(false);
        }
    };

    const handleGitHub = async () => {
        if (!acceptedTerms) return;
        if (!isConfigured) {
            alert("Firebase is not configured.\n\nTo enable sign-in, create a Firebase project and add your credentials to:\nfrontend/nexus-scraper-ui/.env.local\n\nSee .env.local.example for the required variables.");
            return;
        }
        setAuthError(null);
        setAuthLoading(true);
        try {
            await signInWithGitHub();
            console.log("[Auth] GitHub sign-in succeeded");
            router.replace("/");
        } catch (e: any) {
            console.error("[Auth] GitHub sign-in failed:", e.code, e.message);
            const msg = e.code === 'auth/popup-closed-by-user'
                ? "Sign-in popup was closed. Please try again."
                : e.code === 'auth/popup-blocked'
                ? "Popup was blocked by your browser. Please allow popups for this site and try again."
                : e.code === 'auth/account-exists-with-different-credential'
                ? "An account already exists with this email using a different provider. Try signing in with Google."
                : e.code === 'auth/cancelled-oauth-flow'
                ? "OAuth flow was cancelled."
                : e.message || "GitHub sign-in failed. Please try again.";
            setAuthError(msg);
        } finally {
            setAuthLoading(false);
        }
    };

    const handleLocalContinue = () => {
        // Set local session flag so page.tsx allows dashboard access
        localStorage.setItem("aria_local_session", "active");
        router.push("/");
    };

    const isDark = theme === "dark";

    return (
        <div className="min-h-screen flex relative overflow-hidden">
            {/* Background orbs */}
            <div className="orb" style={{ width: 600, height: 600, top: -200, left: -200, background: "rgba(16, 185, 129, 0.5)" }} />
            <div className="orb" style={{ width: 500, height: 500, bottom: -150, right: -150, background: "rgba(6, 182, 212, 0.4)", animationDelay: "-7s" }} />
            <div className="orb" style={{ width: 300, height: 300, top: "50%", left: "40%", background: "rgba(139, 92, 246, 0.3)", animationDelay: "-12s" }} />

            {/* Theme toggle — top right */}
            <button
                onClick={toggleTheme}
                className="fixed top-6 right-6 z-50 w-10 h-10 rounded-xl theme-toggle-btn flex items-center justify-center transition-all duration-300 hover:scale-110"
            >
                {isDark ? <Sun size={17} className="text-amber-400" /> : <Moon size={17} className="text-violet-500" />}
            </button>

            {/* ── LEFT — Branding Panel ───────────────────────────── */}
            <div className="hidden lg:flex flex-col justify-center flex-1 pl-16 pr-12 relative z-10">
                <motion.div
                    initial={{ opacity: 0, x: -40 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    {/* Logo */}
                    <div className="flex items-center space-x-3 mb-8">
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-xl shadow-emerald-500/25">
                            <Sparkles size={26} className="text-white" />
                        </div>
                    </div>

                    <h1 className="text-8xl font-black tracking-tighter leading-none mb-6">
                        <span className="text-transparent bg-clip-text bg-gradient-to-br from-emerald-300 via-teal-200 to-cyan-300">
                            Aria
                        </span>
                    </h1>
                    <p className="text-gray-400 text-xl leading-relaxed font-medium max-w-lg mb-12">
                        Extract <span className="text-white font-bold">structured data</span> from any webpage.
                        <br />No coding, no selectors — <span className="text-emerald-400 font-bold">just paste a URL</span>.
                    </p>

                    {/* Feature grid */}
                    <div className="grid grid-cols-2 gap-3 max-w-lg mb-10">
                        {FEATURES.map((f, i) => (
                            <motion.div
                                key={f.title}
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.3 + i * 0.1 }}
                                className="glass-card rounded-xl p-4 space-y-2.5 login-feature-card"
                            >
                                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center feature-icon-glow">
                                    <f.icon size={16} className="text-emerald-400" />
                                </div>
                                <div>
                                    <p className="text-white text-sm font-bold tracking-tight">{f.title}</p>
                                    <p className="text-gray-400 text-[11px] leading-relaxed mt-1">{f.desc}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    {/* Trust badges */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.7 }}
                        className="flex items-center space-x-3"
                    >
                        {["Open Source", "Self-Hosted", "Zero Tracking", "BYOK"].map((badge) => (
                            <span
                                key={badge}
                                className="text-[10px] font-semibold px-3 py-1.5 rounded-full border border-emerald-500/15 text-emerald-500/70 bg-emerald-500/5 uppercase tracking-wide"
                            >
                                {badge}
                            </span>
                        ))}
                    </motion.div>
                </motion.div>
            </div>

            {/* ── RIGHT — Login Card ─────────────────────────────── */}
            <div className="flex-1 flex items-center justify-center p-8 relative z-10">
                <motion.div
                    initial={{ opacity: 0, y: 30, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.15 }}
                    className="w-full max-w-md"
                >
                    {/* Mobile logo */}
                    <div className="lg:hidden text-center mb-10">
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-xl shadow-emerald-500/25 mx-auto mb-5">
                            <Sparkles size={26} className="text-white" />
                        </div>
                        <h1 className="text-6xl font-black tracking-tighter">
                            <span className="text-transparent bg-clip-text bg-gradient-to-br from-emerald-300 via-teal-200 to-cyan-300">Aria</span>
                        </h1>
                        <p className="text-gray-500 text-sm mt-3 font-medium">AI-powered web data extraction</p>
                    </div>

                    {/* ── Liquid Glass Card ── */}
                    <div className="liquid-glass rounded-3xl p-9 space-y-7">
                        <div className="text-center">
                            <h2 className="text-white text-3xl font-black tracking-tight mb-2">Create your account</h2>
                            <p className="text-gray-400 text-base font-medium">Sign in to get <span className="text-emerald-400 font-bold">10 free extractions</span> daily</p>
                        </div>

                        {/* Privacy acceptance */}
                        <label className="flex items-start space-x-3 cursor-pointer group">
                            <div className="relative mt-0.5">
                                <input
                                    type="checkbox"
                                    checked={acceptedTerms}
                                    onChange={(e) => setAcceptedTerms(e.target.checked)}
                                    className="sr-only"
                                />
                                <div className={`w-5 h-5 rounded-md border-2 transition-all duration-200 flex items-center justify-center ${acceptedTerms
                                        ? "bg-emerald-500 border-emerald-500"
                                        : "border-gray-600 group-hover:border-gray-400"
                                    }`}>
                                    {acceptedTerms && (
                                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                            <path d="M2.5 6L5 8.5L9.5 4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                    )}
                                </div>
                            </div>
                            <span className="text-gray-400 text-sm leading-relaxed">
                                I agree to the{" "}
                                <Link href="/terms" className="text-emerald-400 hover:text-emerald-300 font-semibold transition-colors">Terms of Service</Link>
                                {" "}and{" "}
                                <Link href="/privacy" className="text-emerald-400 hover:text-emerald-300 font-semibold transition-colors">Privacy Policy</Link>
                            </span>
                        </label>

                        {/* Auth Error */}
                        {authError && (
                            <div className="flex items-start space-x-2.5 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="text-red-400 flex-shrink-0 mt-0.5" stroke="currentColor" strokeWidth="2">
                                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                                </svg>
                                <p className="text-red-400 text-xs leading-relaxed">{authError}</p>
                            </div>
                        )}

                        <div className="space-y-3">
                            {/* Google */}
                            <button
                                onClick={handleGoogle}
                                disabled={!acceptedTerms || authLoading}
                                className={`w-full flex items-center justify-center space-x-3 bg-white text-gray-800 font-semibold py-4 px-5 rounded-2xl transition-all duration-200 shadow-sm login-btn-google ${acceptedTerms && !authLoading
                                        ? "hover:bg-gray-50 hover:shadow-md cursor-pointer"
                                        : "opacity-40 cursor-not-allowed"
                                    }`}
                            >
                                {authLoading ? (
                                    <svg className="animate-spin h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                                    </svg>
                                ) : (
                                    <svg width="20" height="20" viewBox="0 0 24 24">
                                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                    </svg>
                                )}
                                <span className="text-base">{authLoading ? "Signing in..." : "Continue with Google"}</span>
                            </button>

                            {/* GitHub */}
                            <button
                                onClick={handleGitHub}
                                disabled={!acceptedTerms || authLoading}
                                className={`w-full flex items-center justify-center space-x-3 bg-[#161b22] text-white font-semibold py-4 px-5 rounded-2xl transition-all duration-200 border border-white/[0.08] login-btn-github ${acceptedTerms && !authLoading
                                        ? "hover:bg-[#1f2937] hover:border-white/[0.15] cursor-pointer"
                                        : "opacity-40 cursor-not-allowed"
                                    }`}
                            >
                                {authLoading ? (
                                    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                                    </svg>
                                ) : (
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
                                    </svg>
                                )}
                                <span className="text-base">{authLoading ? "Signing in..." : "Continue with GitHub"}</span>
                            </button>
                        </div>

                        {/* Divider */}
                        <div className="flex items-center space-x-3">
                            <div className="flex-1 h-px bg-white/[0.06] login-divider" />
                            <Lock size={13} className="text-gray-600" />
                            <div className="flex-1 h-px bg-white/[0.06] login-divider" />
                        </div>

                        {/* Security notice */}
                        <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-4">
                            <div className="flex items-start space-x-2.5">
                                <Shield size={15} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                                <div>
                                    <p className="text-emerald-400 text-xs font-bold mb-1 tracking-wide">Privacy-first architecture</p>
                                    <p className="text-gray-500 text-[11px] leading-relaxed">
                                        Your data is processed locally. Extraction history syncs
                                        securely to your account. We never store your API keys.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Stats */}
                        <div className="grid grid-cols-3 gap-2">
                            {[
                                { value: "100%", label: "Local Processing" },
                                { value: "0", label: "Data Stored" },
                                { value: "BYOK", label: "API Security" },
                            ].map((stat) => (
                                <div key={stat.label} className="text-center py-3 rounded-xl bg-white/[0.02] login-stat-card">
                                    <p className="text-emerald-400 text-base font-black tracking-tight">{stat.value}</p>
                                    <p className="text-gray-600 text-[9px] mt-0.5 font-semibold uppercase tracking-wider">{stat.label}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Footer */}
                    <p className="text-center text-gray-600 text-[10px] mt-6 font-medium">
                        Built with Web Extraction Engine + Google Gemini AI
                    </p>
                </motion.div>
            </div>
        </div>
    );
}
