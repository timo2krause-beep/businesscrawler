from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://scraper:scraper@localhost:5433/scraper"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 Tage

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_basic: str = ""   # Stripe Price ID für Basic
    stripe_price_pro: str = ""     # Stripe Price ID für Pro
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # GitHub (API-Zugriff für Repo-Monitoring)
    github_token: str = ""

    # --- Social Login (OAuth2) ---
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    microsoft_oauth_client_id: str = ""
    microsoft_oauth_client_secret: str = ""
    microsoft_oauth_tenant: str = "common"  # "common" erlaubt private + Business-Konten

    facebook_oauth_client_id: str = ""
    facebook_oauth_client_secret: str = ""

    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""

    # Apple "Sign in with Apple" – erfordert kostenpflichtigen Apple Developer Account.
    apple_oauth_client_id: str = ""       # Services ID, z.B. "de.firma.scraper.web"
    apple_oauth_team_id: str = ""         # Apple Developer Team ID
    apple_oauth_key_id: str = ""          # Key ID des .p8 Signierschlüssels
    apple_oauth_private_key: str = ""     # Inhalt der .p8 Datei (PEM), \n als Zeilenumbrüche

    # OpenRouter AI
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-4-31b-it:free"

    # Google (Places API + Gemini AI)
    google_places_api_key: str = ""
    google_ai_api_key: str = ""  # Gemini API Key für KI-Analysen

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "reports@example.com"

    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
