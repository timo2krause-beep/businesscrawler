"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/api";
import { saveToken } from "@/lib/auth";
import SocialLoginButtons from "@/components/SocialLoginButtons";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const oauthError = searchParams.get("oauth_error");
    if (oauthError) setError(oauthError);
  }, [searchParams]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await login(email, password);
      saveToken(data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      <div className="w-full max-w-[380px]">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-10">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-200">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
          </div>
          <span className="font-bold text-[18px] text-[var(--text-primary)] tracking-tight">
            Scraper
          </span>
        </div>

        <div className="rounded-2xl border border-[var(--border)] bg-white p-8 card-shadow">
          <h1 className="text-[18px] font-bold text-[var(--text-primary)] text-center mb-1">
            Willkommen zurück
          </h1>
          <p className="text-[13px] text-[var(--text-muted)] text-center mb-6">
            Melde dich an, um fortzufahren
          </p>

          <SocialLoginButtons />

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-[12px] px-4 py-3 rounded-xl">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                </svg>
                {error}
              </div>
            )}

            <div>
              <label className="block text-[12px] font-semibold text-[var(--text-secondary)] mb-1.5">
                E-Mail
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2.5 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl text-[13px] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                placeholder="name@firma.de"
              />
            </div>

            <div>
              <label className="block text-[12px] font-semibold text-[var(--text-secondary)] mb-1.5">
                Passwort
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-2.5 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl text-[13px] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                placeholder="Mindestens 8 Zeichen"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-gradient-to-b from-indigo-500 to-indigo-600 text-white rounded-xl text-[13px] font-semibold hover:from-indigo-600 hover:to-indigo-700 transition-all shadow-sm shadow-indigo-200 disabled:opacity-50 mt-2"
            >
              {loading ? "Wird angemeldet..." : "Anmelden"}
            </button>
          </form>
        </div>

        <p className="text-center text-[12px] text-[var(--text-muted)] mt-5">
          Noch kein Konto?{" "}
          <Link href="/register" className="text-indigo-600 font-semibold hover:text-indigo-700 transition-colors">
            Registrieren
          </Link>
        </p>
      </div>
    </div>
  );
}
