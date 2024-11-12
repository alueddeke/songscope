import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css";
import CsrfProvider from "./components/CsrfProvider";

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
      <body className={inter.className + " bg-stone-950"}>
        <CsrfProvider>{children}</CsrfProvider>
      </body>
    </html>
  );
}
