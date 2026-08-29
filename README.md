# Scraper Platform

Modulare SaaS-Plattform für automatisierte Wettbewerbsbeobachtung, Monitoring und Reporting.
Python/FastAPI-Backend + Next.js-Frontend, deutschsprachige UI.

Für Architektur-Details (DB-Schema, AI-Integration, Auth-Flow etc.) siehe [CLAUDE.md](./CLAUDE.md).

## Setup

```bash
# Backend
source .venv/bin/activate
python -m uvicorn app:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Datenbank (PostgreSQL via Docker, Port 5433)
docker compose up -d
```

## Neues Modul hinzufügen

Jedes Modul erbt von `BaseModule` (`core/base_module.py`) und implementiert die Pipeline
`fetch_data()` → `process_data()` → `generate_report()`. Das `name`-Attribut (snake_case,
eindeutig) ist der Schlüssel, unter dem das Modul überall im System referenziert wird — von der
Registry bis zur Persistierung. Ein bereits angelegter, aber noch nicht verdrahteter Kandidat
liegt als Referenz für "vorher" in `modules/foerdermittel_tracker/`.

Damit ein neues Modul **überall** berücksichtigt wird, sind folgende Schritte nötig:

### Pflicht — sonst läuft oder erscheint das Modul nicht

1. **`app.py`**: Modul importieren, `registry.register(DeinModul())` registrieren (API-Backend).
2. **`scheduler.py`**: dieselbe Registrierung duplizieren. Der Wochenreport-Scheduler ist ein
   eigener Prozess — beide Stellen müssen manuell synchron gehalten werden.
3. **`frontend/src/lib/modules.ts`**: Eintrag in `MODULE_INFO` mit `label`, `description`,
   `icon`, `color`, `category` (`"marketing" | "tech"`). `icon`/`color` müssen bereits in
   `frontend/src/components/ModuleCard.tsx` existieren (`ModuleIcon`-Map, `COLOR_MAP`) — sonst
   dort zuerst ergänzen. `VISIBLE_MODULES` wird automatisch aus `MODULE_INFO` abgeleitet, kein
   manueller Eintrag nötig.

### Optional — je nach Funktionsumfang des Moduls

4. **Nutzer-Einstellungen (Preferences)**, falls das Modul pro Nutzer konfigurierbar sein soll:
   - `core/personalization.py` → `build_personalized_module()`: neuen
     `if name == "dein_modul" and "<pref_key>" in prefs:`-Zweig ergänzen, der aus den
     Preferences eine personalisierte Instanz baut. Wird automatisch von `api/module_router.py`
     **und** `scheduler.py` genutzt — nur eine Stelle pflegen.
   - `frontend/src/lib/modules.ts`: `pref_key` / `pref_type` / `pref_placeholder` am
     `MODULE_INFO`-Eintrag setzen. `pref_type` steuert, welcher Editor auf der Modul-Seite
     erscheint: `"targets"` (URL+Name+Selector-Liste), `"company"` (Hinweis auf globalen
     Firmennamen aus Account), `"competitors"` (Wettbewerber-Cache, siehe Punkt 6), oder ganz
     weglassen für die generische String-Listen-UI (nur `pref_key` + `pref_placeholder` nötig).
   - Passt keine der bestehenden `pref_type`-Varianten, muss `renderSettings()` in
     `frontend/src/app/modules/page.tsx` um einen neuen Zweig erweitert werden.

5. **KI-Nutzung**, falls das Modul `ai_chat()` / `ai_json()` aufruft:
   - Jedem Call-Site einen stabilen `task`-Key mitgeben, z. B. `"dein_modul.dein_task"`.
   - `core/ai_routing.py` → `TASKS`-Dict: Eintrag
     `"dein_modul.dein_task": ("<Anzeigename Modul>", "<Beschreibung Prompt>")` ergänzen, damit
     der Task in der Admin-Oberfläche ("KI-Konfiguration") auftaucht und der Provider
     (Gemini/OpenRouter) umschaltbar ist.
   - `core/ai_prompts.py` → `_defaults()`: Lazy-Import der Prompt-Konstante(n) des Moduls plus
     Eintrag im `_DEFAULT_PROMPTS`-Dict mit demselben `task_key`, damit der Code-Default in der
     Admin-UI sichtbar, versioniert und editierbar ist.
   - Token-Tracking (`core/ai_usage.py`) und Token-Limits (`core/plan_config.py`) sind
     vollständig generisch — hier ist nichts zu tun.

6. **Wettbewerber-Cache wiederverwenden**: nur relevant, wenn das Modul auf dieselben gecachten
   Wettbewerber-Profile zugreifen soll wie `ki_wettbewerb` / `social_media_generator`
   (`core/competitor_store.py`, `pref_type: "competitors"`, `/competitors`-Endpunkte in
   `api/company_router.py`).

### Bereits generisch — hier ist nichts anzufassen

`core/registry.py`, `api/module_router.py` (außer dem bewusst modul-spezifischen
`/modules/ki_wettbewerb/refresh`-Endpoint), `core/ai_usage.py`, `core/plan_config.py`,
`api/schemas.py` (`PreferenceSet`).

### Danach nicht vergessen

- **`CLAUDE.md`**: Modulanzahl/-liste unter "Current modules" aktualisieren.
- **`frontend/src/app/reports/page.tsx`** (`MODULE_TITLES`): optionaler, hübscherer
  Report-Titel — fällt sonst automatisch auf `getModuleLabel()` zurück.
- Checks laufen lassen: `ruff check .` + `pytest -q` (Backend), `npm run lint` + `npm run build`
  (Frontend).
