'use client';

import { Activity, Cpu, Shield, Zap } from 'lucide-react';

interface StatusIndicatorProps {
    label: string;
    status: 'online' | 'standby' | 'offline';
}

const StatusIndicator = ({ label, status }: StatusIndicatorProps) => {
    const configs = {
        online: { bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500' },
        standby: { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500' },
        offline: { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500' },
    };

    const config = configs[status];

    return (
        <div className={`status-pill ${config.bg} ${config.text}`}>
            <div className={`w-2 h-2 rounded-full ${config.dot}`} />
            <span>{label}</span>
        </div>
    );
};

export default function CommandCenter() {
    return (
        <header className="bg-[#1a1a1a] border-b border-[#333] fixed top-0 w-full z-50 rounded-t-xl">
            <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
                {/* Traffic Lights */}
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-[#ff5f56] border border-[#e0443e]" />
                    <div className="w-3 h-3 rounded-full bg-[#ffbd2e] border border-[#dea123]" />
                    <div className="w-3 h-3 rounded-full bg-[#27c93f] border border-[#1aab29]" />
                </div>

                {/* Title */}
                <div className="flex items-center gap-2 absolute left-1/2 transform -translate-x-1/2">
                    <span className="text-gray-400 font-mono text-sm tracking-wide">nexus_scraper_v2.0</span>
                </div>

                {/* Status Indicators */}
                <div className="flex items-center gap-4">
                    <StatusIndicator label="API" status="online" />
                </div>
            </div>
        </header>
    );
}
