'use client';

import { useState } from 'react';
import { Search, Loader2, Settings2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface InputModuleProps {
    onRunExtraction: (url: string, config: ScraperConfig) => void;
    isScanning: boolean;
}

export interface ScraperConfig {
    stealthMode: boolean;
    headlessMode: boolean;
    geminiParsing: boolean;
    deepScroll: boolean;
}

export default function InputModule({ onRunExtraction, isScanning }: InputModuleProps) {
    const [url, setUrl] = useState('');
    const [showSettings, setShowSettings] = useState(false);
    const [config, setConfig] = useState<ScraperConfig>({
        stealthMode: true,
        headlessMode: true,
        geminiParsing: true,
        deepScroll: false,
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (url.trim() && !isScanning) {
            onRunExtraction(url, config);
        }
    };

    const toggleConfig = (key: keyof ScraperConfig) => {
        setConfig((prev) => ({ ...prev, [key]: !prev[key] }));
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
        >
            {/* URL Input */}
            <form onSubmit={handleSubmit}>
                <div className="flex items-center gap-3 bg-black/50 border border-glass-border rounded-lg px-2 py-2 focus-within:border-neon-cyan focus-within:shadow-[0_0_15px_rgba(0,229,255,0.3)] transition-all">
                    <div className="pl-3">
                        <span className="text-neon-green font-mono text-lg">{'>'}</span>
                    </div>
                    <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="ENTER_TARGET_URL..."
                        className="flex-1 bg-transparent outline-none text-neon-green placeholder:text-gray-700 font-mono text-sm py-3"
                        disabled={isScanning}
                        autoComplete="off"
                    />
                    <button
                        type="button"
                        onClick={() => setShowSettings(!showSettings)}
                        className="p-2 rounded hover:bg-white/5 transition-colors"
                    >
                        <Settings2 className={`w-5 h-5 ${showSettings ? 'text-neon-cyan' : 'text-gray-500'}`} />
                    </button>
                </div>

                {/* Run Button */}
                <motion.button
                    type="submit"
                    disabled={!url.trim() || isScanning}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    className="btn-primary w-full mt-4 py-4 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
                >
                    {isScanning ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>INITIALIZING PROTOCOL...</span>
                        </>
                    ) : (
                        <span>INITIATE SCAN</span>
                    )}
                </motion.button>
            </form>

            {/* Configuration Toggles */}
            {showSettings && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-6 pt-6 border-t border-gray-200"
                >
                    <h3 className="text-sm font-semibold text-charcoal mb-4">Extraction Settings</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <ToggleSwitch
                            label="Stealth Mode"
                            description="Bypass detection"
                            checked={config.stealthMode}
                            onChange={() => toggleConfig('stealthMode')}
                            disabled={isScanning}
                        />
                        <ToggleSwitch
                            label="Headless"
                            description="Hidden browser"
                            checked={config.headlessMode}
                            onChange={() => toggleConfig('headlessMode')}
                            disabled={isScanning}
                        />
                        <ToggleSwitch
                            label="AI Parsing"
                            description="Use Gemini AI"
                            checked={config.geminiParsing}
                            onChange={() => toggleConfig('geminiParsing')}
                            disabled={isScanning}
                        />
                        <ToggleSwitch
                            label="Deep Scroll"
                            description="Load all content"
                            checked={config.deepScroll}
                            onChange={() => toggleConfig('deepScroll')}
                            disabled={isScanning}
                        />
                    </div>
                </motion.div>
            )}
        </motion.div>
    );
}

interface ToggleSwitchProps {
    label: string;
    description: string;
    checked: boolean;
    onChange: () => void;
    disabled?: boolean;
}

function ToggleSwitch({ label, description, checked, onChange, disabled }: ToggleSwitchProps) {
    return (
        <div
            onClick={!disabled ? onChange : undefined}
            className={`glass-panel rounded p-4 cursor-pointer transition-all border ${checked ? 'border-neon-green/50 bg-neon-green/5' : 'border-glass-border hover:bg-white/5'
                } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
            <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">{label}</span>
                <div
                    className={`w-8 h-4 rounded-full transition-colors ${checked ? 'bg-neon-green' : 'bg-gray-700'
                        }`}
                >
                    <motion.div
                        layout
                        className={`w-3 h-3 rounded-full mt-0.5 ${checked ? 'bg-black' : 'bg-gray-400'}`}
                        style={{ marginLeft: checked ? '18px' : '2px' }}
                    />
                </div>
            </div>
            <p className="text-[10px] text-gray-500 font-mono">{description}</p>
        </div>
    );
}
