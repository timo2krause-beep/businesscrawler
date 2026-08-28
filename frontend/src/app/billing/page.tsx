"use client";

import { useEffect, useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import { getMe, createCheckout, cancelSubscription } from "@/lib/api";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "0",
    color: "from-slate-500 to-slate-600",
    features: ["Plattform-Zugang", "Keine Module"],
  },
  {
    id: "basic",
    name: "Basic",
    price: "29",
    color: "from-blue-500 to-blue-600",
    features: ["1 Modul", "Wöchentliche Reports", "E-Mail Versand"],
  },
  {
    id: "pro",
    name: "Pro",
    price: "79",
    color: "from-indigo-500 to-purple-600",
    popular: true,
    features: [
      "Alle Module",
      "Wöchentliche Reports",
      "E-Mail Versand",
      "Personalisierung",
      "Priority Support",
    ],
  },
];

export default function BillingPage() {
  const [currentPlan, setCurrentPlan] = useState("free");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    getMe().then((me) => setCurrentPlan(me.plan));
  }, []);

  async function handleUpgrade(plan: string) {
    setError("");
    setLoading(plan);

    try {
      const { checkout_url } = await createCheckout(plan);
      window.location.href = checkout_url;
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(null);
    }
  }

  async function handleCancel() {
    if (!confirm("Abo wirklich kündigen?")) return;
    setError("");
    setLoading("cancel");

    try {
      await cancelSubscription();
      setCurrentPlan("free");
      setSuccess("Abo wird zum Periodenende gekündigt.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(null);
    }
  }

  return (
    <DashboardShell>
      <div className="mb-8">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Billing</h1>
        <p className="text-[13px] text-[var(--text-muted)] mt-1">
          Aktueller Plan:{" "}
          <span className="text-[var(--text-primary)] capitalize font-semibold">{currentPlan}</span>
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-[12px] px-4 py-3 rounded-xl mb-4">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-700 text-[12px] px-4 py-3 rounded-xl mb-4">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
          {success}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {PLANS.map((plan) => {
          const isCurrent = plan.id === currentPlan;
          const isUpgrade =
            PLANS.findIndex((p) => p.id === plan.id) >
            PLANS.findIndex((p) => p.id === currentPlan);

          return (
            <div
              key={plan.id}
              className={`rounded-2xl border overflow-hidden transition-all duration-200 ${
                isCurrent
                  ? "border-indigo-200 ring-2 ring-indigo-100"
                  : "border-[var(--border)] hover:border-[var(--border-light)] card-shadow card-shadow-hover"
              }`}
            >
              {/* Header gradient */}
              <div className={`h-2 bg-gradient-to-r ${plan.color}`} />

              <div className="p-6 bg-white relative">
                {"popular" in plan && plan.popular && (
                  <div className="absolute top-4 right-4 px-2.5 py-1 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-[10px] font-bold rounded-full uppercase tracking-wider">
                    Beliebt
                  </div>
                )}

                <h3 className="text-[16px] font-bold text-[var(--text-primary)]">{plan.name}</h3>
                <div className="mt-3 mb-5">
                  <span className="text-3xl font-extrabold text-[var(--text-primary)]">
                    {plan.price}&euro;
                  </span>
                  <span className="text-[var(--text-muted)] text-[13px]"> /Monat</span>
                </div>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2.5 text-[13px] text-[var(--text-secondary)]">
                      <div className="w-5 h-5 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
                        <svg className="w-3 h-3 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      </div>
                      {f}
                    </li>
                  ))}
                </ul>

                {isCurrent ? (
                  <div className="space-y-2">
                    <div className="w-full py-2.5 text-center text-[12px] font-semibold text-indigo-600 bg-indigo-50 rounded-xl">
                      Aktueller Plan
                    </div>
                    {plan.id !== "free" && (
                      <button
                        onClick={handleCancel}
                        disabled={loading === "cancel"}
                        className="w-full py-2 text-center text-[11px] text-[var(--text-muted)] hover:text-red-500 transition-colors"
                      >
                        {loading === "cancel" ? "..." : "Abo kündigen"}
                      </button>
                    )}
                  </div>
                ) : isUpgrade ? (
                  <button
                    onClick={() => handleUpgrade(plan.id)}
                    disabled={loading === plan.id}
                    className={`w-full py-2.5 bg-gradient-to-b ${plan.color} text-white rounded-xl text-[13px] font-semibold hover:opacity-90 transition-all shadow-sm disabled:opacity-50`}
                  >
                    {loading === plan.id ? "Laden..." : `Upgrade auf ${plan.name}`}
                  </button>
                ) : (
                  <div className="w-full py-2.5 text-center text-[12px] text-[var(--text-muted)] rounded-xl">
                    &mdash;
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </DashboardShell>
  );
}
