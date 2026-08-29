"""AI Service: Google Gemini (bevorzugt) oder OpenRouter als Fallback."""

import json
import logging

import httpx

from config.settings import settings
from core.ai_usage import record_usage

log = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# OpenRouter Fallback-Modelle (absteigend nach Qualität)
FALLBACK_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
]


def _resolve_task_config(task: str | None, system: str) -> tuple[str, str]:
    """Lädt die admin-konfigurierte Provider-Wahl und einen evtl. Prompt-Override für einen
    Task. Fällt auf ('auto', system) zurück, wenn kein Task angegeben oder die DB nicht
    erreichbar ist."""
    if not task:
        return "auto", system
    try:
        from core.ai_prompts import get_effective_prompt_or_default
        from core.ai_routing import get_provider
        from core.database import get_session
        with get_session() as db:
            provider = get_provider(db, task)
            effective_system = get_effective_prompt_or_default(db, task, system)
        return provider, effective_system
    except Exception as e:
        log.warning("Konnte KI-Konfiguration für Task '%s' nicht laden (%s), nutze Defaults", task, e)
        return "auto", system


async def ai_chat(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    task: str | None = None,
) -> str:
    """Sendet eine KI-Anfrage. `task` steuert (falls admin-konfiguriert) den Provider und
    einen evtl. Prompt-Override, sonst: Google Gemini wenn Key vorhanden, sonst OpenRouter."""
    provider, system = _resolve_task_config(task, system)

    if provider == "gemini":
        if not settings.google_ai_api_key:
            raise RuntimeError("GOOGLE_AI_API_KEY nicht konfiguriert")
        return await _gemini_chat(prompt, system, temperature, max_tokens)

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY nicht konfiguriert")
        return await _openrouter_chat(prompt, system, model, temperature, max_tokens)

    # "auto": Google Gemini direkt nutzen wenn API Key vorhanden, sonst OpenRouter
    if settings.google_ai_api_key:
        try:
            return await _gemini_chat(prompt, system, temperature, max_tokens)
        except Exception as e:
            log.warning("Gemini fehlgeschlagen: %s, Fallback auf OpenRouter", e)

    if not settings.openrouter_api_key:
        raise RuntimeError("Kein KI-API-Key konfiguriert (GOOGLE_AI_API_KEY oder OPENROUTER_API_KEY)")

    return await _openrouter_chat(prompt, system, model, temperature, max_tokens)


async def _gemini_chat(
    prompt: str,
    system: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """Direkte Google Gemini API."""
    model = "gemini-2.5-flash"
    url = f"{GEMINI_URL}/{model}:generateContent?key={settings.google_ai_api_key}"

    body: dict = {
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},  # Thinking deaktivieren für schnellere, volle Antworten
        },
    }

    # System instruction (offizieller Weg bei Gemini)
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    body["contents"] = [{"role": "user", "parts": [{"text": prompt}]}]

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()

    data = resp.json()
    usage = data.get("usageMetadata", {})
    record_usage(usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0))

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini: Keine Antwort erhalten")

    # Text aus allen Parts zusammensetzen (Thinking-Parts filtern)
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [p.get("text", "") for p in parts if "text" in p and not p.get("thought")]
    if not text_parts:
        # Fallback: alle Parts nehmen
        text_parts = [p.get("text", "") for p in parts if "text" in p]
    return "".join(text_parts)


async def _openrouter_chat(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """OpenRouter mit Modell-Fallback-Kette."""
    import asyncio as _asyncio

    primary_model = model or settings.openrouter_model

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

    for model_name in models_to_try:
        # Manche Modelle (z.B. Gemma) unterstützen keine system-Messages
        if model_name != primary_model and system:
            msgs = [{"role": "user", "content": f"{system}\n\n---\n\n{prompt}"}]
        else:
            msgs = messages

        for attempt in range(2):
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name,
                        "messages": msgs,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )

                if resp.status_code in (429, 400, 404):
                    if attempt == 0 and resp.status_code == 429:
                        log.warning("Rate-Limit (429) für %s, retry in 3s", model_name)
                        await _asyncio.sleep(3)
                        continue
                    else:
                        log.warning("%d für %s, versuche Fallback", resp.status_code, model_name)
                        break

                resp.raise_for_status()

            data = resp.json()
            usage = data.get("usage", {})
            record_usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))

            content = data["choices"][0]["message"]["content"]
            if model_name != primary_model:
                log.info("Fallback-Modell %s verwendet", model_name)
            return content

    raise RuntimeError("Alle KI-Modelle sind rate-limited. Bitte warte kurz und versuche es erneut.")


async def ai_json(
    prompt: str,
    system: str = "",
    model: str | None = None,
    max_tokens: int = 4000,
    task: str | None = None,
) -> dict | list:
    """Wie ai_chat, aber parst die Antwort als JSON."""
    raw = await ai_chat(prompt, system=system, model=model, max_tokens=max_tokens, task=task)

    # JSON aus Markdown-Codeblock extrahieren falls vorhanden
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    # Robustes JSON-Parsing mit mehreren Fallback-Strategien
    for attempt, txt in enumerate(_json_parse_attempts(cleaned)):
        try:
            return json.loads(txt, strict=False)
        except json.JSONDecodeError:
            continue

    # Letzter Versuch: JSON-Objekt/-Array mit Regex extrahieren
    import re
    match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', cleaned)
    if match:
        for txt in _json_parse_attempts(match.group(1)):
            try:
                return json.loads(txt, strict=False)
            except json.JSONDecodeError:
                continue

    raise json.JSONDecodeError("Konnte kein gültiges JSON aus KI-Antwort extrahieren", cleaned, 0)


def _json_parse_attempts(text: str):
    """Generiert zunehmend bereinigte Versionen des Texts."""
    import re
    # 1. Original
    yield text
    # 2. Kommentare + trailing commas entfernen
    cleaned = re.sub(r'//[^\n]*', '', text)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    yield cleaned
    # 3. Steuerzeichen in Strings escapen (Zeilenumbrüche etc.)
    cleaned = re.sub(r'(?<=": ")(.*?)(?="[,\s}\]])', lambda m: m.group(0).replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'), cleaned, flags=re.DOTALL)
    yield cleaned
    # 4. Alle nackten Zeilenumbrüche innerhalb von Strings reparieren
    cleaned = _fix_newlines_in_strings(cleaned)
    yield cleaned


def _fix_newlines_in_strings(text: str) -> str:
    """Ersetzt Zeilenumbrüche innerhalb von JSON-Strings durch \\n."""
    result = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == '\\':
            escape = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
        if in_string and ch == '\n':
            result.append('\\n')
            continue
        if in_string and ch == '\r':
            result.append('\\r')
            continue
        if in_string and ch == '\t':
            result.append('\\t')
            continue
        result.append(ch)
    return ''.join(result)
