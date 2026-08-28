"""Stripe-Integration: Checkout und Webhook-Verarbeitung."""

import logging

import stripe

from config.settings import settings

log = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key

PLAN_LIMITS = {
    "free": 1,
    "basic": 1,
    "pro": 99,
}

# Monatlicher KI-Token-Deckel pro Plan (Summe aus prompt_tokens + completion_tokens
# über alle Modul-Läufe). Verhindert, dass ein einzelner User die KI-API-Kosten
# unkontrolliert hochtreibt. None = kein Limit.
AI_TOKEN_LIMITS: dict[str, int | None] = {
    "free": 50_000,
    "basic": 300_000,
    "pro": 2_000_000,
}


def get_price_id(plan: str) -> str:
    prices = {"basic": settings.stripe_price_basic, "pro": settings.stripe_price_pro}
    price_id = prices.get(plan)
    if not price_id:
        raise ValueError(f"Kein Stripe Price für Plan '{plan}' konfiguriert")
    return price_id


def create_checkout_session(user_id: int, email: str, plan: str) -> str:
    """Erstellt eine Stripe Checkout Session und gibt die URL zurück."""
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": get_price_id(plan), "quantity": 1}],
        success_url=f"{settings.frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/payment/cancel",
        metadata={"user_id": str(user_id), "plan": plan},
    )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verifiziert und parsed einen Stripe Webhook."""
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )


def cancel_subscription(stripe_subscription_id: str) -> None:
    """Kündigt ein Stripe-Abo."""
    stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
    log.info("Subscription %s wird zum Periodenende gekündigt", stripe_subscription_id)
