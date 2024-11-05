"use client";

import { useEffect } from "react";
import { fetchCsrfToken } from "@/services/axios";

export default function CsrfProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    fetchCsrfToken();
  }, []);

  return <>{children}</>;
}
