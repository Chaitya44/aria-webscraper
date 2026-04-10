import Link from "next/link";

export default function PrivacyPage() {
    return (
        <div className="min-h-screen relative">
            <div className="orb" style={{ width: 400, height: 400, top: -100, left: -100, background: "rgba(16, 185, 129, 0.4)" }} />
            <div className="max-w-3xl mx-auto px-6 py-16 relative z-10">
                <Link href="/" className="text-emerald-500/60 hover:text-emerald-400 text-sm transition-colors mb-8 inline-block">
                    ← Back to Aria
                </Link>

                <h1 className="text-4xl font-bold text-white mb-2">Privacy Policy</h1>
                <p className="text-gray-500 text-sm mb-10">Last updated: February 2026</p>

                <div className="space-y-8 text-gray-400 text-sm leading-relaxed">
                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">1. Information We Collect</h2>
                        <p>Aria collects the following information when you use our service:</p>
                        <ul className="list-disc ml-5 mt-2 space-y-1">
                            <li><strong className="text-gray-300">URLs you submit</strong> — to perform web data extraction</li>
                            <li><strong className="text-gray-300">Extraction results</strong> — stored locally in your browser (last 5 queries)</li>
                            <li><strong className="text-gray-300">Authentication data</strong> — email and profile name via Google/GitHub OAuth</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">2. How We Use Your Data</h2>
                        <p>Your data is used solely to provide the web extraction service. We do not sell, rent, or share your personal information with third parties. Extraction results are processed via Google Gemini AI and are subject to Google&apos;s data processing terms.</p>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">3. Data Storage</h2>
                        <p>Scraping history is stored exclusively in your browser&apos;s localStorage. We do not maintain server-side databases of your extraction results. Your history is automatically limited to the 5 most recent queries.</p>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">4. Third-Party Services</h2>
                        <ul className="list-disc ml-5 space-y-1">
                            <li><strong className="text-gray-300">Google Gemini AI</strong> — for data extraction and structuring</li>
                            <li><strong className="text-gray-300">Google OAuth / GitHub OAuth</strong> — for authentication</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">5. Your Rights</h2>
                        <p>You can clear all stored data at any time by clearing your browser&apos;s localStorage. You may also request deletion of your account by contacting us.</p>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">6. Contact</h2>
                        <p>For privacy-related inquiries, reach out via the project&apos;s GitHub repository.</p>
                    </section>
                </div>
            </div>
        </div>
    );
}
