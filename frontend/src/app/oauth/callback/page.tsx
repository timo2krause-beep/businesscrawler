"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { saveToken } from "@/lib/auth";

export default function OAuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    const hash = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
    const params = new URLSearchParams(hash);
    const token = params.get("token");

    if (!token) {
      setError("Anmeldung fehlgeschlagen. Bitte versuche es erneut.");
      return;
    }

    saveToken(token);
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      <div className="w-full max-w-[380px] text-center">
        {error ? (
          <div className="rounded-2xl border border-[var(--border)] bg-white p-8 card-shadow">
            <p className="text-[13px] text-red-700 mb-4">{error}</p>
            <Link href="/login" className="text-indigo-600 font-semibold text-[13px] hover:text-indigo-700">
              Zurück zum Login
            </Link>
          </div>
        ) : (
          <p className="text-[13px] text-[var(--text-muted)]">Anmeldung wird abgeschlossen...</p>
        )}
      </div>
    </div>
  );
}
