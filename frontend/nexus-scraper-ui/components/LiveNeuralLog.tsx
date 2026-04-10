'use client';

import { useEffect, useRef, useState } from 'react';
import { Activity, CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface LogEntry {
    timestamp: string;
    message: string;
}

interface LiveNeuralLogProps {
    logs: LogEntry[];
    isActive: boolean;
}

// Determine log type based on message content
function getLogType(message: string): 'success' | 'error' | 'warning' | 'info' {
    if (message.includes('✓') || message.includes('complete') || message.includes('Connected')) return 'success';
    if (message.includes('❌') || message.includes('Error')) return 'error';
    if (message.includes('⚠️') || message.includes('Warning')) return 'warning';
    return 'info';
}

const PHASES = [
    "Initializing Neural Net...",
    "Hydrating DOM...",
    "Traversing Nodes...",
    "Structuring Data..."
];

export default function LiveNeuralLog({ logs, isActive }: LiveNeuralLogProps) {
    const terminalRef = useRef<HTMLDivElement>(null);
    const [timer, setTimer] = useState(0);
    const [phaseIndex, setPhaseIndex] = useState(0);

    // Live Timer
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isActive) {
            setTimer(0);
            setPhaseIndex(0);
            interval = setInterval(() => {
                setTimer(prev => prev + 0.1);
            }, 100);
        }
        return () => clearInterval(interval);
    }, [isActive]);

    // Phase Cycler
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isActive) {
            interval = setInterval(() => {
                setPhaseIndex(prev => (prev + 1) % PHASES.length);
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [isActive]);

    // Auto-scroll
    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="w-full font-mono">
            {/* Header */}
            <div className="flex items-center justify-between mb-4 px-2">
                <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-neon-cyan" />
                    <span className="text-sm text-neon-cyan tracking-widest">SYSTEM_KERNEL</span>
                </div>
                {isActive && (
                    <div className="flex items-center gap-2 bg-white/5 px-3 py-1 rounded-full border border-white/10">
                        <div className="w-2 h-2 bg-neon-emerald rounded-full animate-pulse" />
                        <span className="text-xs text-white">⏱️ {timer.toFixed(1)}s</span>
                    </div>
                )}
            </div>

            {/* Content Area */}
            <div
                ref={terminalRef}
                className="bg-black/50 border border-white/10 rounded-lg p-5 h-64 overflow-y-auto relative"
            >
                {isActive ? (
                    <div className="space-y-4">
                        {/* Skeleton Loader - Pulsing Bars */}
                        <div className="space-y-2 animate-pulse">
                            <div className="h-2 bg-white/10 rounded w-3/4"></div>
                            <div className="h-2 bg-white/10 rounded w-1/2"></div>
                            <div className="h-2 bg-white/10 rounded w-5/6"></div>
                            <div className="h-2 bg-white/5 rounded w-full"></div>
                            <div className="h-2 bg-white/5 rounded w-2/3"></div>
                        </div>

                        {/* Phase Status */}
                        <div className="mt-8 flex flex-col items-center justify-center text-center">
                            <Loader2 className="w-8 h-8 text-neon-cyan animate-spin mb-3" />
                            <p className="text-neon-cyan text-sm tracking-widest uppercase animate-pulse">
                                {PHASES[phaseIndex]}
                            </p>
                            <p className="text-[10px] text-gray-500 mt-1">
                                PROCESSING_VECTOR_EMBEDDINGS
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-1">
                        {logs.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-gray-600">
                                <span className="opacity-20 text-4xl mb-2">⌘</span>
                                <p className="text-xs tracking-widest">AWAITING_COMMAND</p>
                            </div>
                        ) : (
                            logs.map((log, index) => (
                                <div key={index} className="flex gap-3 text-gray-400 font-xs hover:bg-white/5 p-1 rounded transition-colors">
                                    <span className="text-gray-600 shrink-0">[{log.timestamp}]</span>
                                    <span className={log.message.includes("✓") ? "text-neon-emerald" : "text-gray-300"}>
                                        {log.message.replace(/^[✓❌⚠️]\s*/, '> ')}
                                    </span>
                                </div>
                            ))
                        )}
                        {!isActive && logs.length > 0 && <span className="text-neon-cyan animate-pulse">_</span>}
                    </div>
                )}
            </div>
        </div>
    );
}
