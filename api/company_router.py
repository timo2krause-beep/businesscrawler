"""Company Endpoint: Globaler Firmenname + KI-Branchenerkennung + Wettbewerber-Verwaltung."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from core.ai_service import ai_json
from core.database import get_db
from core.models import CompetitorProfile, User, UserPreference

router = APIRouter(tags=["Company"])

# Branche → relevante Review-Plattformen
INDUSTRY_PLATFORMS: dict[str, list[str]] = {
    "restaurant": ["google", "trustpilot", "provenexpert", "tripadvisor", "golocal", "11880"],
    "hotel": ["google", "trustpilot", "provenexpert", "tripadvisor", "11880"],
    "gastro": ["google", "trustpilot", "provenexpert", "tripadvisor", "golocal", "11880"],
    "handwerk": ["google", "provenexpert", "11880", "golocal", "kennstdueinen"],
    "dienstleistung": ["google", "trustpilot", "kununu", "provenexpert", "11880", "kennstdueinen"],
    "saas": ["google", "trustpilot", "kununu", "glassdoor", "appstore", "playstore"],
    "software": ["google", "trustpilot", "kununu", "glassdoor", "appstore", "playstore"],
    "app": ["google", "trustpilot", "appstore", "playstore"],
    "ecommerce": ["google", "trustpilot", "provenexpert", "ekomi", "trustedshops"],
    "beratung": ["google", "trustpilot", "kununu", "provenexpert", "kennstdueinen"],
    "arzt": ["google", "provenexpert", "jameda", "11880", "kennstdueinen"],
    "gesundheit": ["google", "trustpilot", "kununu", "provenexpert", "jameda"],
    "einzelhandel": ["google", "trustpilot", "provenexpert", "golocal", "11880"],
    "bildung": ["google", "trustpilot", "kununu", "provenexpert"],
    "immobilien": ["google", "trustpilot", "kununu", "provenexpert", "11880"],
    "finanzen": ["google", "trustpilot", "kununu", "glassdoor", "provenexpert", "ekomi"],
    "logistik": ["google", "trustpilot", "kununu", "provenexpert"],
    "default": ["google", "trustpilot", "kununu", "glassdoor", "provenexpert"],
}

CLASSIFY_PROMPT = """Du bist ein Branchen-Klassifikator. Der User gibt Firmeninfos an.
Antworte NUR mit einem JSON-Objekt (kein anderer Text):
{
  "industry": "<branche>",
  "industry_label": "<Branche auf Deutsch, z.B. 'Restaurant & Gastronomie'>",
  "has_app": true/false,
  "is_local": true/false
}

Verwende eine dieser Branchen-Keys:
restaurant, hotel, gastro, handwerk, dienstleistung, saas, software, app, ecommerce, beratung, arzt, gesundheit, einzelhandel, bildung, immobilien, finanzen, logistik

"has_app" ist true wenn das Unternehmen wahrscheinlich eine mobile App hat.
"is_local" ist true wenn das Unternehmen primär lokal/regional agiert (z.B. Restaurant, Handwerker, Arzt, lokaler Einzelhandel). false bei überregionalen/internationalen Firmen (SaaS, E-Commerce, Ketten mit >10 Standorten).

Wenn du die Firma nicht kennst, rate basierend auf dem Namen und ggf. dem Standort."""

COMPANY_SIZES = ["solo", "klein", "mittel", "gross", "konzern"]
COMPANY_SIZE_LABELS = {
    "solo": "Einzelunternehmen",
    "klein": "Kleinunternehmen (2-20 MA)",
    "mittel": "Mittelstand (20-250 MA)",
    "gross": "Großunternehmen (250+ MA)",
    "konzern": "Konzern / Kette",
}


class CompanySetRequest(BaseModel):
    company_name: str
    location: str = ""
    company_size: str = ""


class CompanyResponse(BaseModel):
    company_name: str
    location: str
    company_size: str
    company_size_label: str
    industry: str
    industry_label: str
    is_local: bool
    platforms: list[str]


def _upsert_pref(db: Session, user_id: int, key: str, value):
    existing = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id, UserPreference.key == key)
        .first()
    )
    if existing:
        existing.value = value
    else:
        db.add(UserPreference(user_id=user_id, key=key, value=value))


@router.get("/company", response_model=CompanyResponse)
def get_company(user: User = Depends(get_current_user)):
    """Gibt das globale Firmenprofil des Users zurück."""
    prefs = {p.key: p.value for p in user.preferences}
    size = prefs.get("company_size", "")
    return CompanyResponse(
        company_name=prefs.get("company_name", ""),
        location=prefs.get("company_location", ""),
        company_size=size,
        company_size_label=COMPANY_SIZE_LABELS.get(size, ""),
        industry=prefs.get("company_industry", ""),
        industry_label=prefs.get("company_industry_label", ""),
        is_local=prefs.get("company_is_local", False),
        platforms=prefs.get("company_platforms", []),
    )


@router.put("/company", response_model=CompanyResponse)
async def set_company(
    req: CompanySetRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Setzt den globalen Firmennamen und erkennt die Branche per KI."""
    name = req.company_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Firmenname darf nicht leer sein")

    location = req.location.strip()
    company_size = req.company_size if req.company_size in COMPANY_SIZES else ""

    # KI-Branchenerkennung mit Kontext
    classify_input = f"Firma: {name}"
    if location:
        classify_input += f"\nStandort: {location}"
    if company_size:
        classify_input += f"\nGröße: {COMPANY_SIZE_LABELS.get(company_size, company_size)}"

    try:
        result = await ai_json(classify_input, system=CLASSIFY_PROMPT)
        industry = result.get("industry", "default")
        industry_label = result.get("industry_label", "Unbekannt")
        has_app = result.get("has_app", False)
        is_local = result.get("is_local", False)
    except Exception:
        industry = "default"
        industry_label = "Unbekannt"
        has_app = False
        is_local = bool(location)

    # Plattformen basierend auf Branche
    platforms = INDUSTRY_PLATFORMS.get(industry, INDUSTRY_PLATFORMS["default"])[:]
    if has_app and "appstore" not in platforms:
        platforms.append("appstore")
        platforms.append("playstore")

    # Preferences speichern
    _upsert_pref(db, user.id, "company_name", name)
    _upsert_pref(db, user.id, "company_location", location)
    _upsert_pref(db, user.id, "company_size", company_size)
    _upsert_pref(db, user.id, "company_industry", industry)
    _upsert_pref(db, user.id, "company_industry_label", industry_label)
    _upsert_pref(db, user.id, "company_is_local", is_local)
    _upsert_pref(db, user.id, "company_platforms", platforms)
    db.commit()

    return CompanyResponse(
        company_name=name,
        location=location,
        company_size=company_size,
        company_size_label=COMPANY_SIZE_LABELS.get(company_size, ""),
        industry=industry,
        industry_label=industry_label,
        is_local=is_local,
        platforms=platforms,
    )


# --- Competitors ---


class CompetitorOut(BaseModel):
    id: int
    name: str
    url: str
    reason: str
    is_custom: bool
    is_active: bool

    model_config = {"from_attributes": True}


class CompetitorAddRequest(BaseModel):
    name: str
    url: str = ""


class CompetitorToggleRequest(BaseModel):
    is_active: bool


@router.get("/competitors", response_model=list[CompetitorOut])
def list_competitors(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gibt alle Wettbewerber (KI + eigene) für den User zurück."""
    prefs = {p.key: p.value for p in user.preferences}
    company = prefs.get("company_name", "")
    if not company:
        return []

    rows = (
        db.query(CompetitorProfile)
        .filter(CompetitorProfile.company_name == company.lower())
        .order_by(CompetitorProfile.is_custom, CompetitorProfile.id)
        .all()
    )
    return [
        CompetitorOut(
            id=r.id,
            name=r.competitor_name,
            url=r.competitor_url,
            reason=r.competitor_data.get("reason", "Manuell hinzugefügt") if r.competitor_data else "Manuell hinzugefügt",
            is_custom=r.is_custom,
            is_active=r.is_active,
        )
        for r in rows
    ]


@router.post("/competitors", response_model=CompetitorOut)
def add_competitor(
    req: CompetitorAddRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fügt einen eigenen Wettbewerber hinzu."""
    prefs = {p.key: p.value for p in user.preferences}
    company = prefs.get("company_name", "")
    if not company:
        raise HTTPException(status_code=400, detail="Kein Firmenname konfiguriert")

    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")

    # Duplikat prüfen
    existing = (
        db.query(CompetitorProfile)
        .filter(
            CompetitorProfile.company_name == company.lower(),
            CompetitorProfile.competitor_name == name,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"'{name}' ist bereits als Wettbewerber vorhanden")

    row = CompetitorProfile(
        company_name=company.lower(),
        competitor_name=name,
        competitor_url=req.url.strip(),
        competitor_data={"name": name, "url": req.url.strip(), "reason": "Manuell hinzugefügt"},
        is_custom=True,
        is_active=True,
        needs_refresh=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return CompetitorOut(
        id=row.id,
        name=row.competitor_name,
        url=row.competitor_url,
        reason="Manuell hinzugefügt",
        is_custom=True,
        is_active=True,
    )


@router.patch("/competitors/{competitor_id}")
def toggle_competitor(
    competitor_id: int,
    req: CompetitorToggleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aktiviert/deaktiviert einen Wettbewerber."""
    prefs = {p.key: p.value for p in user.preferences}
    company = prefs.get("company_name", "")

    row = (
        db.query(CompetitorProfile)
        .filter(
            CompetitorProfile.id == competitor_id,
            CompetitorProfile.company_name == company.lower(),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Wettbewerber nicht gefunden")

    row.is_active = req.is_active
    db.commit()
    return {"detail": f"{'Aktiviert' if req.is_active else 'Deaktiviert'}: {row.competitor_name}"}


@router.delete("/competitors/{competitor_id}")
def delete_competitor(
    competitor_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Löscht einen eigenen Wettbewerber."""
    prefs = {p.key: p.value for p in user.preferences}
    company = prefs.get("company_name", "")

    row = (
        db.query(CompetitorProfile)
        .filter(
            CompetitorProfile.id == competitor_id,
            CompetitorProfile.company_name == company.lower(),
            CompetitorProfile.is_custom == True,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Eigener Wettbewerber nicht gefunden")

    db.delete(row)
    db.commit()
    return {"detail": f"Gelöscht: {row.competitor_name}"}
