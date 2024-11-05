import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css";
<<<<<<< HEAD
import CsrfProvider from "./components/CsrfProvider";
=======
// import "../styles/vaiables.scss";
>>>>>>> development

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
<<<<<<< HEAD
      <body className={inter.className}>
        <CsrfProvider>{children}</CsrfProvider>
      </body>
=======
      <body className={inter.className + " bg-brown"}>{children}</body>
>>>>>>> development
    </html>
  );
}
