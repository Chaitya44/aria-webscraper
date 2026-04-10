"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
    User,
    onAuthStateChanged,
    signInWithPopup,
    GoogleAuthProvider,
    GithubAuthProvider,
    signOut as firebaseSignOut,
} from "firebase/auth";
import { auth, isConfigured } from "@/lib/firebase";

interface AuthContextType {
    user: User | null;
    loading: boolean;
    signInWithGoogle: () => Promise<void>;
    signInWithGitHub: () => Promise<void>;
    signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    signInWithGoogle: async () => { },
    signInWithGitHub: async () => { },
    signOut: async () => { },
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!auth || !isConfigured) {
            setLoading(false);
            return;
        }
        const unsubscribe = onAuthStateChanged(auth, (u) => {
            setUser(u);
            setLoading(false);
        });
        return unsubscribe;
    }, []);

    const signInWithGoogle = async () => {
        if (!auth) {
            console.warn("[Auth] Firebase not configured. Add NEXT_PUBLIC_FIREBASE_* env vars.");
            return;
        }
        const provider = new GoogleAuthProvider();
        await signInWithPopup(auth, provider);
    };

    const signInWithGitHub = async () => {
        if (!auth) {
            console.warn("[Auth] Firebase not configured. Add NEXT_PUBLIC_FIREBASE_* env vars.");
            return;
        }
        const provider = new GithubAuthProvider();
        await signInWithPopup(auth, provider);
    };

    const signOut = async () => {
        if (!auth) return;
        // Clear sensitive data from localStorage
        localStorage.removeItem("aria_gemini_key");
        localStorage.removeItem("aria_history");
        localStorage.removeItem("aria_local_session");
        await firebaseSignOut(auth);
    };

    return (
        <AuthContext.Provider value={{ user, loading, signInWithGoogle, signInWithGitHub, signOut }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
