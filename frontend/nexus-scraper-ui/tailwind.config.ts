import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                // Modern Fintech Color Palette
                'neon-lime': '#D4FF00',
                'charcoal': {
                    DEFAULT: '#111111',
                    50: '#3A3A3A',
                    100: '#2A2A2A',
                    200: '#1A1A1A',
                    300: '#111111',
                },
                'light-bg': {
                    DEFAULT: '#F8F8F8',
                    50: '#FFFFFF',
                    100: '#FAFAFA',
                    200: '#F8F8F8',
                    300: '#F0F0F0',
                },
                'subtle-gray': {
                    DEFAULT: '#999999',
                    light: '#CCCCCC',
                    dark: '#666666',
                },
                // Keep electric for accents
                electric: {
                    blue: '#3B82F6',
                    green: '#10B981',
                    purple: '#8B5CF6',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            borderRadius: {
                '3xl': '24px',
                '4xl': '32px',
            },
            boxShadow: {
                'soft': '0 2px 8px rgba(0, 0, 0, 0.04)',
                'card': '0 4px 16px rgba(0, 0, 0, 0.08)',
                'elevated': '0 8px 24px rgba(0, 0, 0, 0.12)',
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-in-out',
                'slide-up': 'slideUp 0.4s ease-out',
                'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
                pulseSoft: {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.7' },
                },
            },
        },
    },
    plugins: [],
};

export default config;
