'use client';

import { Download, Copy, FileJson, Table2, CheckCircle2, FolderOpen, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import { useState } from 'react';

interface MultiEntityData {
    status: string;
    entities: Record<string, any>;
    entityCount: number;
    totalItems: number;
    timestamp: string;
    url: string;
}

interface DataViewProps {
    data: MultiEntityData;
    isVisible: boolean;
    duration: number;
}

// Helper: Convert snake_case to Title Case
function formatCategoryName(key: string): string {
    const name = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    // Add contextual emojis
    const emojis: Record<string, string> = {
        'profile': '👤', 'artist': '🎤', 'product': '📦', 'song': '🎵',
        'album': '💿', 'review': '⭐', 'price': '💰', 'related': '🔗',
        'tour': '🎫', 'headline': '📰', 'trending': '🔥', 'item': '📋',
        'top': '🏆', 'list': '📝', 'info': 'ℹ️', 'detail': '📄'
    };

    for (const [word, emoji] of Object.entries(emojis)) {
        if (key.toLowerCase().includes(word)) {
            return `${emoji} ${name}`;
        }
    }
    return `📋 ${name}`;
}

// Helper: Render cell value
function renderCellValue(key: string, value: any): JSX.Element {
    if (value === null || value === undefined) return <span className="text-subtle-gray">-</span>;

    if (Array.isArray(value)) {
        if (value.length === 0) return <span className="text-subtle-gray">-</span>;
        if (value.every(item => typeof item === 'string' || typeof item === 'number')) {
            const joined = value.join(', ');
            return <span className="text-charcoal">{joined.length > 60 ? joined.slice(0, 60) + '...' : joined}</span>;
        }
        return <span className="text-electric-blue text-xs font-medium px-2 py-1 bg-blue-50 rounded-full">{value.length} items</span>;
    }

    if (typeof value === 'object') {
        return <span className="text-subtle-gray text-xs">{JSON.stringify(value).slice(0, 40)}...</span>;
    }

    if (typeof value === 'string' && (key.includes('url') || key.includes('link')) && value.startsWith('http')) {
        return <a href={value} target="_blank" rel="noopener noreferrer" className="text-electric-blue hover:underline text-sm">View →</a>;
    }

    if (key.includes('price') || key.includes('salary') || key.includes('cost')) {
        return <span className="text-green-600 font-semibold">{String(value)}</span>;
    }

    const strValue = String(value);
    return <span className="text-charcoal">{strValue.length > 80 ? strValue.slice(0, 80) + '...' : strValue}</span>;
}

export default function DataView({ data, isVisible, duration }: DataViewProps) {
    const [activeCategory, setActiveCategory] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);

    if (!isVisible || !data || !data.entities) return null;

    const categories = Object.entries(data.entities);

    // Set initial active category
    if (activeCategory === null && categories.length > 0) {
        setActiveCategory(categories[0][0]);
    }

    const handleCopyJSON = () => {
        navigator.clipboard.writeText(JSON.stringify(data.entities, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDownloadCategory = (key: string, value: any) => {
        const isArray = Array.isArray(value);
        const content = isArray
            ? convertToCSV(value)
            : JSON.stringify(value, null, 2);

        const blob = new Blob([content], { type: isArray ? 'text/csv' : 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${key}-${Date.now()}.${isArray ? 'csv' : 'json'}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const convertToCSV = (items: any[]): string => {
        if (items.length === 0) return '';
        const headers = Object.keys(items[0]);
        const csvHeader = headers.join(',');
        const csvRows = items.map(item =>
            headers.map(h => {
                const val = item[h];
                if (val === null || val === undefined) return '""';
                if (typeof val === 'object') return `"${JSON.stringify(val).replace(/"/g, '""')}"`;
                return `"${String(val).replace(/"/g, '""')}"`;
            }).join(',')
        ).join('\n');
        return csvHeader + '\n' + csvRows;
    };

    return (
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-black border border-[#333] rounded-xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-[#333] bg-[#0a0a0a]">
                <div className="flex items-center gap-4">
                    <FolderOpen className="w-5 h-5 text-neon-cyan" />
                    <h3 className="font-mono text-white text-sm tracking-wider uppercase">EXTRACTED_DATA_matrix</h3>
                    <span className="bg-[#111] border border-[#333] text-gray-400 px-3 py-1 rounded text-xs font-mono">
                        {data.entityCount} NODES • {data.totalItems} ITEMS
                    </span>
                    {duration < 12 && (
                        <span className="flex items-center gap-2 bg-neon-emerald/10 border border-neon-emerald/30 text-neon-emerald px-3 py-1 rounded text-xs font-mono">
                            <Zap className="w-3 h-3" />
                            FAST_SCRAPE ({duration.toFixed(1)}s)
                        </span>
                    )}
                </div>
                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleCopyJSON}
                    className="text-xs font-mono flex items-center gap-2 px-3 py-1.5 bg-[#222] hover:bg-[#333] text-gray-300 rounded transition-colors"
                >
                    <Copy className="w-3 h-3" />
                    {copied ? 'COPIED' : 'JSON'}
                </motion.button>
            </div>

            {/* Category Tabs */}
            <div className="flex gap-1 p-2 bg-[#050505] border-b border-[#333] overflow-x-auto">
                {categories.map(([key]) => (
                    <button
                        key={key}
                        onClick={() => setActiveCategory(key)}
                        className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wide transition-all ${activeCategory === key
                            ? 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/50'
                            : 'text-gray-500 hover:text-gray-300 hover:bg-[#111]'
                            }`}
                    >
                        {formatCategoryName(key)}
                    </button>
                ))}
            </div>

            {/* Active Category Content */}
            {activeCategory && (
                <div className="bg-black min-h-[300px]">
                    {renderCategoryContent(
                        activeCategory,
                        data.entities[activeCategory],
                        handleDownloadCategory
                    )}
                </div>
            )}
        </motion.div>
    );
}

function renderCategoryContent(key: string, value: any, onDownload: (k: string, v: any) => void) {
    // SANITIZATION
    if (typeof value === 'string' && value.includes('[object Object]')) {
        return <div className="p-8 text-red-500 font-mono text-sm border-l-2 border-red-500 ml-4 mt-4">ERROR: CORRUPTED_DATA_STREAM</div>;
    }

    if (Array.isArray(value) && value.length > 0) {
        const headers = Object.keys(value[0]);

        return (
            <div>
                <div className="overflow-x-auto max-h-[500px] scrollbar-thin scrollbar-thumb-gray-800">
                    <table className="w-full text-xs font-mono text-left">
                        <thead className="bg-[#111] sticky top-0 z-10">
                            <tr>
                                {headers.map(h => (
                                    <th key={h} className="py-3 px-4 text-neon-cyan border-b border-[#333] uppercase tracking-wider font-semibold">
                                        {h.replace(/_/g, ' ')}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1a1a1a]">
                            {value.map((item: any, idx: number) => (
                                <tr key={idx} className="hover:bg-[#0a0a0a] transition-colors group">
                                    {headers.map(h => (
                                        <td key={h} className="py-2.5 px-4 text-gray-300 border-r border-[#1a1a1a] last:border-0 truncate max-w-xs group-hover:text-white">
                                            {renderCellValue(h, item[h])}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <div className="p-3 border-t border-[#333] bg-[#0a0a0a] flex justify-between items-center">
                    <span className="text-gray-600 text-[10px] font-mono">{value.length} RECORDS EXTRACTED</span>
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => onDownload(key, value)}
                        className="text-neon-emerald hover:text-white text-xs font-mono flex items-center gap-2 px-3 py-1"
                    >
                        <Download className="w-3 h-3" />
                        DOWNLOAD.CSV
                    </motion.button>
                </div>
            </div>
        );
    } else if (typeof value === 'object' && value !== null) {
        return (
            <div className="p-8">
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(value).map(([k, v]) => {
                        if (String(v).includes('[object Object]')) return null;

                        return (
                            <div key={k} className="group">
                                <span className="text-[10px] text-neon-cyan uppercase tracking-widest block mb-1">
                                    {k.replace(/_/g, ' ')}
                                </span>
                                <div className="text-sm text-gray-300 font-mono border-l border-[#333] pl-3 py-1 group-hover:border-neon-cyan/50 transition-colors break-words">
                                    {typeof v === 'string' && v.startsWith('http')
                                        ? <a href={v} target="_blank" rel="noopener noreferrer" className="text-neon-emerald hover:underline underline-offset-4">{v}</a>
                                        : String(v)
                                    }
                                </div>
                            </div>
                        )
                    })}
                </div>
                <div className="mt-8 pt-4 border-t border-[#333] flex justify-end">
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => onDownload(key, value)}
                        className="text-neon-cyan hover:text-white text-xs font-mono flex items-center gap-2"
                    >
                        <FileJson className="w-3 h-3" />
                        DOWNLOAD.JSON
                    </motion.button>
                </div>
            </div>
        );
    }

    return <div className="p-12 text-gray-600 font-mono text-center text-xs tracking-widest">DATA_VECTOR_EMPTY</div>;
}
