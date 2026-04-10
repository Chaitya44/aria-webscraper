"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import NexusDashboard from "@/components/NexusDashboard";

export default function Home() {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.replace("/login");
        }
    }, [user, loading, router]);

    // Still resolving auth
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 rounded-full border-2 border-emerald-500/30 border-t-emerald-500 animate-spin" />
            </div>
        );
    }

    // Authenticated → render dashboard
    if (user) {
        return <NexusDashboard />;
    }

    // Waiting for redirect
    return null;
}
