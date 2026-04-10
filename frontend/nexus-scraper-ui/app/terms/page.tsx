import Link from "next/link";

export default function TermsPage() {
    return (
        <div className="min-h-screen relative">
            <div className="orb" style={{ width: 400, height: 400, top: -100, right: -100, background: "rgba(6, 182, 212, 0.4)" }} />
            <div className="max-w-3xl mx-auto px-6 py-16 relative z-10">
                <Link href="/" className="text-emerald-500/60 hover:text-emerald-400 text-sm transition-colors mb-8 inline-block">
                    ← Back to Aria
                </Link>

                <h1 className="text-4xl font-bold text-white mb-2">Terms of Service</h1>
                <p className="text-gray-500 text-sm mb-10">Last updated: February 2026</p>

                <div className="space-y-8 text-gray-400 text-sm leading-relaxed">
                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">1. Acceptance of Terms</h2>
                        <p>By using Aria, you agree to these Terms of Service. If you do not agree, please do not use the service.</p>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">2. Description of Service</h2>
                        <p>Aria is an AI-powered web data extraction tool. It uses browser automation (DrissionPage) to visit publicly accessible web pages and Google Gemini AI to structure the extracted content into organized datasets.</p>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">3. Acceptable Use</h2>
                        <p>You agree to use Aria only for lawful purposes. You must not:</p>
                        <ul className="list-disc ml-5 mt-2 space-y-1">
                            <li>Scrape websites that explicitly prohibit automated access in their robots.txt or Terms of Service</li>
                            <li>Use extracted data to violate any individual&apos;s privacy</li>
                            <li>Attempt to bypass authentication or access restricted content</li>
                            <li>Use the service for any illegal activity</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">4. Intellectual Property</h2>
                        <p>The data you extract belongs to the original website owners. Aria does not claim ownership of any extracted content. You are responsible for ensuring your use of extracted data complies with applicable laws and the source website&apos;s terms.</p>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">5. Limitation of Liability</h2>
                        <p>Aria is provided &quot;as is&quot; without warranties of any kind. We are not liable for any damages arising from the use of this service, including but not limited to data accuracy, completeness, or legality of extracted content.</p>
                    </section>

                    <section>
                        <h2 className="text-white text-lg font-semibold mb-3">6. Changes to Terms</h2>
                        <p>We reserve the right to update these terms at any time. Continued use of the service constitutes acceptance of modified terms.</p>
                    </section>
                </div>
            </div>
        </div>
    );
}
