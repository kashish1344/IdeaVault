import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "IdeaVault — AI Image & Video Generation",
  description:
    "Generate high-quality images and videos from natural language using our multi-agent AI pipeline.",
  openGraph: {
    title: "IdeaVault",
    description: "AI-powered image & video generation",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans bg-zinc-950 text-white antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
