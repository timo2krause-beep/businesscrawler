"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="de">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, background: "#fff" }}>
        <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center", maxWidth: 400, padding: 24 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
              Etwas ist schiefgelaufen
            </h2>
            <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: 16 }}>
              {error.message || "Ein unerwarteter Fehler ist aufgetreten."}
            </p>
            <button
              onClick={reset}
              style={{
                padding: "10px 20px",
                background: "#6366f1",
                color: "#fff",
                border: "none",
                borderRadius: 12,
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Erneut versuchen
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
