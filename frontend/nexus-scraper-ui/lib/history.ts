import {
    collection,
    addDoc,
    getDocs,
    deleteDoc,
    doc,
    getDoc,
    setDoc,
    updateDoc,
    serverTimestamp,
} from "firebase/firestore";
import { db } from "@/lib/firebase";

export interface HistoryEntry {
    id?: string;
    url: string;
    timestamp: string;
    data: Record<string, any[]>;
    schema: Record<string, any>;
    itemCount: number;
    createdAt?: any;
}

const COLLECTION_PATH = (uid: string) => `users/${uid}/history`;
const MAX_HISTORY = 5;

/**
 * Save a scrape result to Firestore. Enforces FIFO limit of 5.
 * Uses client-side sorting to avoid requiring Firestore composite indexes.
 */
export async function saveHistory(uid: string, entry: Omit<HistoryEntry, "id">) {
    if (!db) {
        console.warn("[History] Firestore not initialized — skipping save");
        return;
    }
    const colRef = collection(db, COLLECTION_PATH(uid));

    // Add the new entry, stringifying 'data' to bypass Firestore nested array limits
    // Also include localMs to prevent serverTimestamp sorting race conditions
    await addDoc(colRef, {
        ...entry,
        data: JSON.stringify(entry.data),
        localMs: Date.now(),
        createdAt: serverTimestamp(),
    });

    // Enforce FIFO: get all docs, sort client-side, delete oldest if over limit
    const snapshot = await getDocs(colRef);
    if (snapshot.size > MAX_HISTORY) {
        // Sort by localMs ascending (oldest first)
        const sorted = snapshot.docs.sort((a, b) => {
            const aTime = a.data().localMs || 0;
            const bTime = b.data().localMs || 0;
            return aTime - bTime;
        });
        const toDelete = snapshot.size - MAX_HISTORY;
        for (let i = 0; i < toDelete; i++) {
            await deleteDoc(doc(db, COLLECTION_PATH(uid), sorted[i].id));
        }
    }
}

/**
 * Load all history entries for a user, newest first.
 * Client-side sorting — no Firestore index required.
 */
export async function loadHistory(uid: string): Promise<HistoryEntry[]> {
    if (!db) {
        console.warn("[History] Firestore not initialized — returning empty");
        return [];
    }
    const colRef = collection(db, COLLECTION_PATH(uid));
    const snapshot = await getDocs(colRef);

    // Sort client-side: newest first (descending)
    const sorted = snapshot.docs.sort((a, b) => {
        const aTime = a.data().localMs || 0;
        const bTime = b.data().localMs || 0;
        return bTime - aTime; // newest first
    });

    return sorted.slice(0, MAX_HISTORY).map((d) => {
        const docData = d.data();
        let parsedData = {};
        try {
            parsedData = typeof docData.data === "string" ? JSON.parse(docData.data) : (docData.data || {});
        } catch (e) {
            parsedData = docData.data || {};
        }

        return {
            id: d.id,
            url: docData.url,
            timestamp: docData.timestamp,
            data: parsedData as any,
            schema: docData.schema,
            itemCount: docData.itemCount,
        };
    });
}

/**
 * Delete a single history entry.
 */
export async function deleteHistoryEntry(uid: string, docId: string) {
    if (!db) return;
    await deleteDoc(doc(db, COLLECTION_PATH(uid), docId));
}

/**
 * Clear all history for a user.
 */
export async function clearHistory(uid: string) {
    if (!db) return;
    const colRef = collection(db, COLLECTION_PATH(uid));
    const snapshot = await getDocs(colRef);
    for (const d of snapshot.docs) {
        await deleteDoc(doc(db, COLLECTION_PATH(uid), d.id));
    }
}

// ── Daily Scrape Tracker ─────────────────────────────────────────────────────

const USER_DOC_PATH = (uid: string) => `users/${uid}`;

export async function getDailyScrapeCount(uid: string): Promise<number> {
    if (!db) return 0;
    const today = new Date().toISOString().slice(0, 10);
    const docRef = doc(db, USER_DOC_PATH(uid));
    const snap = await getDoc(docRef);
    if (snap.exists()) {
        const data = snap.data();
        if (data.lastScrapeDate === today) {
            return data.dailyCount || 0;
        }
    }
    return 0;
}

export async function incrementDailyScrapeCount(uid: string): Promise<void> {
    if (!db) return;
    const today = new Date().toISOString().slice(0, 10);
    const docRef = doc(db, USER_DOC_PATH(uid));
    const snap = await getDoc(docRef);
    if (!snap.exists()) {
        await setDoc(docRef, { lastScrapeDate: today, dailyCount: 1 });
    } else {
        const data = snap.data();
        if (data.lastScrapeDate === today) {
            await updateDoc(docRef, { dailyCount: (data.dailyCount || 0) + 1 });
        } else {
            await updateDoc(docRef, { lastScrapeDate: today, dailyCount: 1 });
        }
    }
}
