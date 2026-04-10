import {
    collection,
    addDoc,
    getDocs,
    deleteDoc,
    doc,
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

    // Add the new entry
    await addDoc(colRef, {
        ...entry,
        createdAt: serverTimestamp(),
    });

    // Enforce FIFO: get all docs, sort client-side, delete oldest if over limit
    const snapshot = await getDocs(colRef);
    if (snapshot.size > MAX_HISTORY) {
        // Sort by createdAt ascending (oldest first), handle missing createdAt
        const sorted = snapshot.docs.sort((a, b) => {
            const aTime = a.data().createdAt?.toMillis?.() || 0;
            const bTime = b.data().createdAt?.toMillis?.() || 0;
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

    // Sort client-side: newest first
    const sorted = snapshot.docs.sort((a, b) => {
        const aTime = a.data().createdAt?.toMillis?.() || 0;
        const bTime = b.data().createdAt?.toMillis?.() || 0;
        return bTime - aTime; // newest first
    });

    return sorted.slice(0, MAX_HISTORY).map((d) => {
        const data = d.data();
        return {
            id: d.id,
            url: data.url,
            timestamp: data.timestamp,
            data: data.data,
            schema: data.schema,
            itemCount: data.itemCount,
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
