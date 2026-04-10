"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { User, Mail, Calendar, Trash2, AlertTriangle, Shield, Key, LogOut, ArrowLeft } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { clearHistory } from "@/lib/history";
import { deleteUser } from "firebase/auth";
import Link from "next/link";

export default function ProfilePage() {
    const router = useRouter();
    const { user, signOut } = useAuth();
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="glass-card gradient-border rounded-2xl p-8 text-center space-y-4 max-w-sm">
                    <User size={40} className="text-gray-600 mx-auto" />
                    <h2 className="text-white text-xl font-bold">Not signed in</h2>
                    <p className="text-gray-500 text-sm">Sign in to manage your account settings.</p>
                    <Link
                        href="/login"
                        className="inline-block bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-2.5 rounded-xl font-medium text-sm hover:from-emerald-400 hover:to-teal-400 transition-all"
                    >
                        Sign In
                    </Link>
                </div>
            </div>
        );
    }

    const handleDeleteAccount = async () => {
        setDeleting(true);
        setError(null);
        try {
            // 1. Clear Firestore history
            await clearHistory(user.uid);

            // 2. Clear local storage
            localStorage.removeItem("aria_history");
            localStorage.removeItem("aria_gemini_key");

            // 3. Delete Firebase Auth account
            await deleteUser(user);

            // 4. Redirect to home
            router.push("/");
        } catch (e: any) {
            if (e.code === "auth/requires-recent-login") {
                setError("For security, please sign out, sign back in, and try again. Firebase requires a recent login to delete accounts.");
            } else {
                setError(e.message || "Failed to delete account. Please try again.");
            }
            setDeleting(false);
        }
    };

    const createdAt = user.metadata?.creationTime
        ? new Date(user.metadata.creationTime).toLocaleDateString("en-US", {
            year: "numeric", month: "long", day: "numeric",
        })
        : "Unknown";

    const provider = user.providerData?.[0]?.providerId === "google.com" ? "Google" :
        user.providerData?.[0]?.providerId === "github.com" ? "GitHub" : "Email";

    return (
        <div className="min-h-screen p-6 md:p-8 text-gray-200 font-sans flex flex-col items-center">
            {/* Back button */}
            <div className="w-full max-w-2xl mb-6">
                <Link href="/" className="inline-flex items-center space-x-2 text-gray-500 hover:text-gray-300 transition-colors text-sm">
                    <ArrowLeft size={16} />
                    <span>Back to Dashboard</span>
                </Link>
            </div>

            {/* Profile Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-2xl"
            >
                <div className="glass-card gradient-border rounded-2xl overflow-hidden">
                    {/* Header Banner */}
                    <div className="h-24 bg-gradient-to-r from-emerald-500/20 via-teal-500/10 to-cyan-500/20 relative">
                        <div className="absolute -bottom-10 left-8">
                            {user.photoURL ? (
                                <img
                                    src={user.photoURL}
                                    alt=""
                                    className="w-20 h-20 rounded-2xl border-4 border-[#0a0a0f] object-cover shadow-xl"
                                    referrerPolicy="no-referrer"
                                />
                            ) : (
                                <div className="w-20 h-20 rounded-2xl border-4 border-[#0a0a0f] bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-xl">
                                    <span className="text-white text-2xl font-bold">
                                        {user.displayName?.charAt(0) || user.email?.charAt(0) || "?"}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="pt-14 p-8 space-y-6">
                        {/* Name & Email */}
                        <div>
                            <h1 className="text-2xl font-bold text-white">{user.displayName || "User"}</h1>
                            <p className="text-gray-500 text-sm mt-1">{user.email}</p>
                        </div>

                        {/* Account Info Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                                <div className="flex items-center space-x-2 mb-2">
                                    <Shield size={14} className="text-emerald-500" />
                                    <span className="text-gray-500 text-xs">Provider</span>
                                </div>
                                <p className="text-white text-sm font-medium">{provider}</p>
                            </div>
                            <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                                <div className="flex items-center space-x-2 mb-2">
                                    <Calendar size={14} className="text-cyan-500" />
                                    <span className="text-gray-500 text-xs">Joined</span>
                                </div>
                                <p className="text-white text-sm font-medium">{createdAt}</p>
                            </div>
                            <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                                <div className="flex items-center space-x-2 mb-2">
                                    <Key size={14} className="text-amber-500" />
                                    <span className="text-gray-500 text-xs">API Key</span>
                                </div>
                                <p className="text-white text-sm font-medium">
                                    {localStorage.getItem("aria_gemini_key") ? (
                                        <span className="text-emerald-400">Configured ✓</span>
                                    ) : (
                                        <span className="text-red-400">Not set</span>
                                    )}
                                </p>
                            </div>
                        </div>

                        {/* Divider */}
                        <div className="h-px bg-white/[0.06]" />

                        {/* Sign Out */}
                        <button
                            onClick={signOut}
                            className="w-full flex items-center justify-center space-x-2 py-3 rounded-xl border border-white/[0.08] text-gray-400 hover:text-white hover:bg-white/[0.04] transition-all text-sm font-medium"
                        >
                            <LogOut size={16} />
                            <span>Sign Out</span>
                        </button>

                        {/* Danger Zone */}
                        <div className="border border-red-500/15 rounded-xl p-5 space-y-4">
                            <div className="flex items-center space-x-2">
                                <AlertTriangle size={16} className="text-red-400" />
                                <h3 className="text-red-400 text-sm font-semibold">Danger Zone</h3>
                            </div>
                            <p className="text-gray-500 text-xs leading-relaxed">
                                Permanently delete your account and all associated data. This action
                                cannot be undone. Your scraping history will be permanently removed.
                            </p>

                            {error && (
                                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                                    <p className="text-red-400 text-xs">{error}</p>
                                </div>
                            )}

                            <AnimatePresence>
                                {!showDeleteConfirm ? (
                                    <motion.button
                                        key="delete-btn"
                                        onClick={() => setShowDeleteConfirm(true)}
                                        className="flex items-center space-x-2 text-red-400/70 hover:text-red-400 text-sm transition-colors"
                                    >
                                        <Trash2 size={14} />
                                        <span>Delete my account</span>
                                    </motion.button>
                                ) : (
                                    <motion.div
                                        key="confirm"
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: "auto" }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="space-y-3 overflow-hidden"
                                    >
                                        <p className="text-red-300 text-xs font-medium">
                                            Are you sure? This will permanently delete your account and all data.
                                        </p>
                                        <div className="flex items-center space-x-3">
                                            <button
                                                onClick={handleDeleteAccount}
                                                disabled={deleting}
                                                className="bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-xs font-medium transition-all disabled:opacity-50"
                                            >
                                                {deleting ? "Deleting..." : "Yes, delete permanently"}
                                            </button>
                                            <button
                                                onClick={() => setShowDeleteConfirm(false)}
                                                className="text-gray-500 hover:text-gray-300 text-xs transition-colors"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
