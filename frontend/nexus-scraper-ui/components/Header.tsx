"use client";

import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun, Moon, User, LogOut, Settings, ChevronDown } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { motion, AnimatePresence } from "framer-motion";

export default function Header() {
    const pathname = usePathname();
    const { user, signOut } = useAuth();
    const [theme, setTheme] = useState<"dark" | "light">("dark");
    const [showMenu, setShowMenu] = useState(false);
    const [isLocked, setIsLocked] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const buttonRef = useRef<HTMLButtonElement>(null);
    const [dropdownPos, setDropdownPos] = useState({ top: 0, right: 0 });
    const [mounted, setMounted] = useState(false);

    useEffect(() => { setMounted(true); }, []);

    useEffect(() => {
        const saved = localStorage.getItem("aria_theme") as "dark" | "light" | null;
        if (saved) {
            setTheme(saved);
            document.documentElement.classList.toggle("light", saved === "light");
        }
    }, []);

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            const target = e.target as Node;
            const dropdownEl = document.getElementById('aria-user-dropdown');
            if (
                menuRef.current && !menuRef.current.contains(target) &&
                (!dropdownEl || !dropdownEl.contains(target))
            ) {
                setShowMenu(false);
            }
        };
        if (showMenu) document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, [showMenu]);

    useEffect(() => {
        const handler = (e: Event) => {
            const detail = (e as CustomEvent).detail;
            setIsLocked(detail?.active ?? false);
            if (detail?.active) setShowMenu(false);
        };
        window.addEventListener('aria-scraping', handler);
        return () => window.removeEventListener('aria-scraping', handler);
    }, []);

    const toggleTheme = () => {
        const next = theme === "dark" ? "light" : "dark";
        setTheme(next);
        localStorage.setItem("aria_theme", next);
        document.documentElement.classList.toggle("light", next === "light");
    };

    if (pathname === "/login") return null;

    const isDark = theme === "dark";

    return (
        <div className={`fixed top-0 right-0 z-[9999] p-4 md:p-6 transition-opacity duration-300 pointer-events-none ${isLocked ? 'opacity-50' : ''}`}>
            <div className="flex items-center justify-end space-x-3 pointer-events-auto">
                {/* Theme toggle */}
                <button
                    onClick={toggleTheme}
                    className="w-9 h-9 rounded-xl theme-toggle-btn flex items-center justify-center transition-all duration-300 hover:scale-105"
                    title={`Switch to ${isDark ? "light" : "dark"} mode`}
                >
                    <AnimatePresence mode="wait">
                        {isDark ? (
                            <motion.div key="sun" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.2 }}>
                                <Sun size={16} className="text-amber-400" />
                            </motion.div>
                        ) : (
                            <motion.div key="moon" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }} transition={{ duration: 0.2 }}>
                                <Moon size={16} className="text-violet-500" />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </button>

                {user ? (
                    <div className="relative user-menu-wrapper" ref={menuRef}>
                        <button
                            ref={buttonRef}
                            onClick={() => {
                                if (!showMenu && buttonRef.current) {
                                    const rect = buttonRef.current.getBoundingClientRect();
                                    setDropdownPos({
                                        top: rect.bottom + 8,
                                        right: window.innerWidth - rect.right,
                                    });
                                }
                                setShowMenu(v => !v);
                            }}
                            className="flex items-center space-x-2 pl-1 pr-2 py-1 rounded-xl border border-white/[0.06] hover:border-white/[0.12] bg-white/[0.03] hover:bg-white/[0.06] transition-all duration-200 user-pill"
                        >
                            {user.photoURL ? (
                                <img
                                    src={user.photoURL}
                                    alt=""
                                    className="w-7 h-7 rounded-lg object-cover"
                                    referrerPolicy="no-referrer"
                                />
                            ) : (
                                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
                                    <span className="text-white text-[11px] font-bold">
                                        {user.displayName?.charAt(0) || "?"}
                                    </span>
                                </div>
                            )}
                            <span className="text-sm font-medium text-white/80 hidden sm:block max-w-[100px] truncate user-name-text">
                                {user.displayName?.split(" ")[0] || "User"}
                            </span>
                            <ChevronDown size={13} className={`text-gray-500 transition-transform duration-200 ${showMenu ? "rotate-180" : ""}`} />
                        </button>

                        {mounted && showMenu && createPortal(
                            <AnimatePresence>
                                <motion.div
                                    id="aria-user-dropdown"
                                    initial={{ opacity: 0, y: -8, scale: 0.97 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: -8, scale: 0.97 }}
                                    transition={{ duration: 0.15 }}
                                    style={{
                                        position: "fixed",
                                        top: dropdownPos.top,
                                        right: dropdownPos.right,
                                        zIndex: 999999,
                                        width: 256,
                                    }}
                                    className="glass-card rounded-2xl border border-white/[0.08] p-2 shadow-2xl dropdown-card"
                                >
                                    <div className="flex items-center space-x-3 px-3 py-3 rounded-xl bg-white/[0.03]">
                                        {user.photoURL ? (
                                            <img
                                                src={user.photoURL}
                                                alt=""
                                                className="w-10 h-10 rounded-xl object-cover ring-2 ring-emerald-500/20"
                                                referrerPolicy="no-referrer"
                                            />
                                        ) : (
                                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center ring-2 ring-emerald-500/20">
                                                <span className="text-white text-sm font-bold">
                                                    {user.displayName?.charAt(0) || "?"}
                                                </span>
                                            </div>
                                        )}
                                        <div className="min-w-0 flex-1">
                                            <p className="text-white text-sm font-semibold truncate dropdown-name">{user.displayName || "User"}</p>
                                            <p className="text-gray-500 text-[11px] truncate dropdown-email">{user.email}</p>
                                        </div>
                                    </div>

                                    <div className="h-px bg-white/[0.06] my-1" />

                                    <Link
                                        href="/profile"
                                        onClick={() => setShowMenu(false)}
                                        className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/[0.04] transition-all text-sm dropdown-item"
                                    >
                                        <Settings size={15} />
                                        <span>Account Settings</span>
                                    </Link>

                                    <button
                                        onClick={async () => {
                                            setShowMenu(false);
                                            await signOut();
                                        }}
                                        className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-red-400 hover:bg-red-500/10 transition-all text-sm"
                                    >
                                        <LogOut size={15} />
                                        <span>Sign out</span>
                                    </button>
                                </motion.div>
                            </AnimatePresence>,
                            document.body
                        )}
                    </div>
                ) : (
                    <Link
                        href="/login"
                        className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white text-sm font-medium transition-all duration-200 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40"
                    >
                        <User size={14} />
                        <span>Sign In</span>
                    </Link>
                )}
            </div>
        </div>
    );
}
