# Feature-Roadmap: Competitive Intelligence Service

Abgeleitet aus Nicos Fahrplan (Validierung → Iteration → Wachstum). Zwei Kategorien:
**Produkt-Features** (bauen wir hier im Code) und **begleitende Aufgaben** (Business/Marketing,
kein Code, nur zur Übersicht/Nachverfolgung).

## Produkt-Features

- [x] **1. Konkrete Handlungsempfehlungen in der KI-Analyse**
  Aktuell liefert `ki_wettbewerb` ein Analyse-Profil (`PROFILE_SYSTEM_PROMPT`), aber keine
  explizit umsetzbaren Empfehlungen ("Erhöhe Preise um X %, da Wettbewerber Y das auch tut").
  Neuer, strukturierter Empfehlungs-Block mit konkreter Handlung + Begründung + Datenbezug.
  *Bezug: Schritt 1 – von Nico direkt als erste Aufgabe für Timo benannt.*

- [ ] **2. Social-Media-Post-Generator (Folgeprodukt)**
  Aus den Konkurrenzdaten automatisch 5–10 fertige Social-Media-Post-Vorlagen generieren
  (Text + Vorschlag für Bildmotiv), direkt kopierbar/downloadbar.
  *Bezug: Schritt 1 – "Folgeprodukt ohne Arbeit für den Kunden".*

- [ ] **3. PDF-Export für Reports**
  Reports existieren bisher nur als Markdown/HTML (`core/report_renderer.py`). Für
  Beispiel-Reports auf der Landing Page und für Kunden-Reports wird ein PDF-Download gebraucht.

- [ ] **4. Pricing-Tiers sauber anbinden (Basis/Premium)**
  `Subscription.plan` kennt schon `free/basic/pro` und Stripe-Price-IDs. Auf Nicos Vorschlag
  (Basis 29 €, Premium 49 €) abstimmen und im Billing-UI klar darstellen.

- [ ] **5. Öffentliche Landing Page mit Lead-Formular**
  Marketing-Seite (kein Login nötig): Headline, Nutzenversprechen, Formular
  (E-Mail, Firmenname, Branche) → löst automatisch einen kostenlosen Test-Report aus.
  *Bezug: Schritt 3.5.*

- [ ] **6. Mini-Analyse-Generator für Kaltakquise-E-Mails**
  Leichtgewichtige Variante der KI-Analyse: aus Firmenname + Branche automatisch eine
  3–4-Sätze-Mini-Analyse für die 1. Kontakt-E-Mail generieren (Grundlage für Schritt 4).

- [ ] **7. Anonymisierter Beispiel-Report als Download**
  Ein Demo-Report (z. B. Lasertag-Test, anonymisiert) als PDF für die Landing Page.
  *Abhängig von Feature 3.*

- [ ] **8. Testimonials-Sektion auf der Landing Page**
  Sobald erste Testnutzer-Zitate vorliegen, auf der Landing Page einbauen.

- [ ] **9. Case-Study-Seite/Vorlage**
  Struktur für "Wie Firma X 15 % mehr Kunden gewann" – Template + Route.

- [ ] **10. Lead-/Kontakt-Tracking (CRM-lite)** *(später, nicht dringend)*
  Aktuell per OneDrive/Excel geplant. Falls das Volumen wächst: einfache interne Ansicht,
  welche Unternehmen kontaktiert wurden, mit Status (E-Mail 1/2, Anruf, Social Media).

## Begleitende Aufgaben (kein Code – zur Übersicht)

- Interner Test mit Nicos Lasertag-Verleih (Schritt 1)
- Test mit 3–5 befreundeten Kleingewerben (Schritt 3)
- Unternehmensliste Emden & Umgebung erstellen (Schritt 4)
- Kontaktstrategie/E-Mail-Texte für Kaltakquise ausarbeiten (Schritt 4)
- Hosting-/Tool-Entscheidungen (E-Mail-Massenversand, OneDrive vs. Office)

## Offene Entscheidungen (aus Nicos Fragen)

- Preismodell für die Testphase: kostenlos vs. 10 €/Monat
- Reihenfolge Kaltakquise: Mini-Analyse schon in E-Mail 1 oder erst in E-Mail 2?
- Zeitplan: 6 Monate bis Launch realistisch?
