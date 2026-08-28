"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-primary)]">
      <div className="text-center max-w-md px-6">
        <div className="w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
        </div>
        <h2 className="text-[16px] font-bold text-[var(--text-primary)] mb-2">
          Etwas ist schiefgelaufen
        </h2>
        <p className="text-[13px] text-[var(--text-muted)] mb-4">
          {error.message || "Ein unerwarteter Fehler ist aufgetreten."}
        </p>
        <button
          onClick={reset}
          className="px-5 py-2.5 bg-gradient-to-b from-indigo-500 to-indigo-600 text-white rounded-xl text-[13px] font-semibold hover:from-indigo-600 hover:to-indigo-700 shadow-sm transition-all"
        >
          Erneut versuchen
        </button>
      </div>
    </div>
  );
}
