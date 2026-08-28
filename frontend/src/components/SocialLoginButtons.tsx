"use client";

import { useEffect, useState } from "react";
import { API_BASE, getOAuthProviders } from "@/lib/api";

const PROVIDERS: {
  id: string;
  label: string;
  icon: React.ReactNode;
}[] = [
  {
    id: "google",
    label: "Mit Google fortfahren",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.47a5.54 5.54 0 0 1-2.4 3.63v3h3.88c2.27-2.09 3.57-5.17 3.57-8.82Z" />
        <path fill="#34A853" d="M12 24c3.24 0 5.95-1.07 7.94-2.91l-3.88-3c-1.08.72-2.45 1.15-4.06 1.15-3.13 0-5.78-2.11-6.73-4.95H1.27v3.1A12 12 0 0 0 12 24Z" />
        <path fill="#FBBC05" d="M5.27 14.29a7.2 7.2 0 0 1 0-4.58v-3.1H1.27a12 12 0 0 0 0 10.78l4-3.1Z" />
        <path fill="#EA4335" d="M12 4.75c1.76 0 3.34.61 4.58 1.8l3.44-3.44C17.94 1.19 15.24 0 12 0A12 12 0 0 0 1.27 6.61l4 3.1C6.22 6.86 8.87 4.75 12 4.75Z" />
      </svg>
    ),
  },
  {
    id: "microsoft",
    label: "Mit Microsoft fortfahren",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24">
        <path fill="#F25022" d="M1 1h10.5v10.5H1z" />
        <path fill="#7FBA00" d="M12.5 1H23v10.5H12.5z" />
        <path fill="#00A4EF" d="M1 12.5h10.5V23H1z" />
        <path fill="#FFB900" d="M12.5 12.5H23V23H12.5z" />
      </svg>
    ),
  },
  {
    id: "facebook",
    label: "Mit Facebook fortfahren",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24">
        <path
          fill="#1877F2"
          d="M24 12.07C24 5.4 18.63 0 12 0S0 5.4 0 12.07C0 18.1 4.39 23.1 10.13 24v-8.44H7.08v-3.49h3.05V9.41c0-3.02 1.79-4.69 4.53-4.69 1.31 0 2.68.24 2.68.24v2.97h-1.51c-1.49 0-1.95.93-1.95 1.89v2.25h3.32l-.53 3.49h-2.79V24C19.61 23.1 24 18.1 24 12.07Z"
        />
      </svg>
    ),
  },
  {
    id: "apple",
    label: "Mit Apple fortfahren",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="#000">
        <path d="M16.36 1.43c0 1.14-.42 2.2-1.15 3.05-.85.98-2.23 1.75-3.44 1.66-.15-1.14.4-2.32 1.13-3.1.83-.9 2.29-1.6 3.46-1.61ZM20.6 17.02c-.5 1.15-.74 1.66-1.38 2.68-.9 1.42-2.16 3.19-3.73 3.2-1.4.02-1.76-.9-3.66-.89-1.9.01-2.3.9-3.7.89-1.57-.02-2.76-1.61-3.66-3.03-2.5-3.9-2.76-8.48-1.22-10.92 1.1-1.73 2.83-2.75 4.46-2.75 1.66 0 2.7.92 4.08.92 1.33 0 2.14-.92 4.08-.92 1.45 0 2.99.79 4.08 2.16-3.59 1.97-3.01 7.09.65 8.66Z" />
      </svg>
    ),
  },
  {
    id: "github",
    label: "Mit GitHub fortfahren",
    icon: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="#181717">
        <path d="M12 0C5.37 0 0 5.4 0 12.07c0 5.35 3.44 9.88 8.21 11.48.6.11.82-.26.82-.58v-2.02c-3.34.73-4.04-1.63-4.04-1.63-.55-1.4-1.34-1.77-1.34-1.77-1.1-.75.08-.74.08-.74 1.21.09 1.85 1.25 1.85 1.25 1.08 1.85 2.82 1.32 3.5 1 .11-.79.42-1.32.77-1.62-2.67-.31-5.47-1.34-5.47-5.96 0-1.32.47-2.39 1.24-3.24-.12-.31-.54-1.56.12-3.25 0 0 1.01-.33 3.3 1.24a11.4 11.4 0 0 1 6 0c2.29-1.57 3.3-1.24 3.3-1.24.66 1.69.24 2.94.12 3.25.77.85 1.24 1.92 1.24 3.24 0 4.63-2.8 5.65-5.48 5.95.43.38.81 1.12.81 2.26v3.35c0 .32.22.7.83.58C20.57 21.94 24 17.41 24 12.07 24 5.4 18.63 0 12 0Z" />
      </svg>
    ),
  },
];

export default function SocialLoginButtons() {
  const [available, setAvailable] = useState<string[] | null>(null);

  useEffect(() => {
    getOAuthProviders()
      .then((res) => setAvailable(res.providers))
      .catch(() => setAvailable([]));
  }, []);

  function startLogin(provider: string) {
    window.location.href = `${API_BASE}/auth/oauth/${provider}/login`;
  }

  if (!available || available.length === 0) return null;

  const providers = PROVIDERS.filter((p) => available.includes(p.id));

  return (
    <div className="mb-5">
      <div className="grid grid-cols-1 gap-2">
        {providers.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => startLogin(p.id)}
            className="w-full flex items-center justify-center gap-2.5 py-2.5 bg-white border border-[var(--border)] rounded-xl text-[13px] font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition-all"
          >
            {p.icon}
            {p.label}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3 mt-5 mb-1">
        <div className="flex-1 h-px bg-[var(--border)]" />
        <span className="text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wide">
          oder mit E-Mail
        </span>
        <div className="flex-1 h-px bg-[var(--border)]" />
      </div>
    </div>
  );
}
