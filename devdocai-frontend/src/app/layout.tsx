import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DevDocAI v3.0.0 - AI-Powered Documentation Generation",
  description: "Generate professional documentation in seconds with DevDocAI's advanced AI engine. Enterprise-quality docs for solo developers.",
  keywords: "documentation, AI, developer tools, code documentation, automated docs, DevDocAI",
  authors: [{ name: "DevDocAI Team" }],
  creator: "DevDocAI",
  publisher: "DevDocAI",
  openGraph: {
    title: "DevDocAI - AI-Powered Documentation Generation",
    description: "Generate professional documentation in seconds with our advanced AI engine.",
    type: "website",
    locale: "en_US",
    siteName: "DevDocAI",
  },
  twitter: {
    card: "summary_large_image",
    title: "DevDocAI - AI-Powered Documentation",
    description: "Enterprise-quality documentation for solo developers",
    creator: "@devdocai",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: "/devdocai-logo.png",
    shortcut: "/devdocai-logo.png",
    apple: "/devdocai-logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased h-full w-full m-0 p-0`}
      >
        <main className="w-full min-h-screen flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
