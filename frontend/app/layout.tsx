import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css";
// import "../styles/vaiables.scss";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SongScope",
  description: "Find the next big hit",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className + " bg-brown"}>{children}</body>
    </html>
  );
}
