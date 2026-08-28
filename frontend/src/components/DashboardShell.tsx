"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import Sidebar from "./Sidebar";

export default function DashboardShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;

  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      <Sidebar />
      <main className="ml-[230px] flex-1 py-8 px-10 max-w-[1100px]">
        <div className="animate-fade-in">{children}</div>
      </main>
    </div>
  );
}
