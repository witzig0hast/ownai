"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    router.replace(isAuthenticated ? "/chat" : "/login");
  }, [isLoading, isAuthenticated, router]);

  return (
    <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">Loading...</div>
  );
}
