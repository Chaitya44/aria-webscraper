import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import { AuthProvider } from "@/contexts/AuthContext";

export const metadata: Metadata = {
    title: "Aria — AI Web Data Extractor",
    description: "Universal web data extraction powered by Google Gemini AI and DrissionPage",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className="antialiased">
                <AuthProvider>
                    <Header />
                    {children}
                </AuthProvider>
            </body>
        </html>
    );
}
