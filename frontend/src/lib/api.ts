export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    throw new Error("Nicht authentifiziert");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Fehler ${res.status}`);
  }

  if (res.status === 204) return {} as T;
  return res.json();
}

// --- Auth ---

export function register(email: string, password: string) {
  return request<{ access_token: string }>("/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string) {
  return request<{ access_token: string }>("/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getOAuthProviders() {
  return request<{ providers: string[] }>("/auth/oauth/providers");
}

export function getMe() {
  return request<{
    id: number;
    email: string;
    is_admin: boolean;
    plan: string;
    modules: string[];
    created_at: string;
  }>("/me");
}

// --- Modules ---

export function getModules() {
  return request<{ modules: { name: string; description: string }[] }>("/modules");
}

export function subscribeModule(module_name: string) {
  return request<{ detail: string }>("/modules/subscribe", {
    method: "POST",
    body: JSON.stringify({ module_name }),
  });
}

export function unsubscribeModule(module_name: string) {
  return request<{ detail: string }>(`/modules/subscribe/${module_name}`, {
    method: "DELETE",
  });
}

export function runModule(name: string) {
  return request<{
    module: string;
    title: string;
    item_count: number;
    markdown: string;
    report_id: number | null;
  }>(`/modules/${name}/run`, { method: "POST" });
}

// --- Preferences ---

export function setPreference(key: string, value: unknown) {
  return request("/modules/preferences", {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  });
}

export function getPreferences() {
  return request<{ key: string; value: unknown }[]>("/modules/preferences");
}

export function refreshCompetitors() {
  return request<{ detail: string; count: number }>("/modules/ki_wettbewerb/refresh", {
    method: "POST",
  });
}

// --- Reports ---

export function getReports(module?: string) {
  const params = module ? `?module=${module}` : "";
  return request<
    { id: number; module: string; content_md: string; created_at: string }[]
  >(`/reports${params}`);
}

export function getReport(id: number) {
  return request<{
    id: number;
    module: string;
    content_md: string;
    content_html: string;
    raw_data: Record<string, unknown> | null;
    created_at: string;
  }>(`/reports/${id}`);
}

// --- Company ---

export interface CompanyProfile {
  company_name: string;
  location: string;
  company_size: string;
  company_size_label: string;
  industry: string;
  industry_label: string;
  is_local: boolean;
  platforms: string[];
}

export function getCompany() {
  return request<CompanyProfile>("/company");
}

export function setCompany(company_name: string, location: string = "", company_size: string = "") {
  return request<CompanyProfile>("/company", {
    method: "PUT",
    body: JSON.stringify({ company_name, location, company_size }),
  });
}

// --- Competitors ---

export interface Competitor {
  id: number;
  name: string;
  url: string;
  reason: string;
  is_custom: boolean;
  is_active: boolean;
}

export function getCompetitors() {
  return request<Competitor[]>("/competitors");
}

export function addCompetitor(name: string, url: string = "") {
  return request<Competitor>("/competitors", {
    method: "POST",
    body: JSON.stringify({ name, url }),
  });
}

export function toggleCompetitor(id: number, is_active: boolean) {
  return request<{ detail: string }>(`/competitors/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ is_active }),
  });
}

export function deleteCompetitor(id: number) {
  return request<{ detail: string }>(`/competitors/${id}`, {
    method: "DELETE",
  });
}

// --- Billing ---

export function getSubscription() {
  return request<{ plan: string; status: string; stripe_customer_id: string | null }>(
    "/subscription"
  );
}

export function createCheckout(plan: string) {
  return request<{ checkout_url: string }>("/checkout", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}

export function cancelSubscription() {
  return request<{ detail: string }>("/subscription/cancel", {
    method: "POST",
  });
}
