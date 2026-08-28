"""Payment Endpoints: Stripe Checkout und Webhooks."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.schemas import CheckoutRequest, CheckoutResponse, SubscriptionResponse
from auth.dependencies import get_current_user
from core.database import get_db
from core.models import Subscription, User, UserModule
from payments.stripe_service import (
    cancel_subscription,
    construct_webhook_event,
    create_checkout_session,
)

log = logging.getLogger(__name__)
router = APIRouter(tags=["Payments"])


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    req: CheckoutRequest,
    user: User = Depends(get_current_user),
):
    if req.plan not in ("basic", "pro"):
        raise HTTPException(status_code=400, detail="Plan muss 'basic' oder 'pro' sein")

    url = create_checkout_session(user.id, user.email, req.plan)
    return CheckoutResponse(checkout_url=url)


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(user: User = Depends(get_current_user)):
    sub = user.subscription
    if not sub:
        raise HTTPException(status_code=404, detail="Kein Abo gefunden")
    return sub


@router.post("/subscription/cancel")
def cancel_sub(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = user.subscription
    if not sub or sub.plan == "free":
        raise HTTPException(status_code=400, detail="Kein aktives Bezahl-Abo")

    if sub.stripe_subscription_id:
        cancel_subscription(sub.stripe_subscription_id)

    sub.status = "cancelled"
    db.commit()
    return {"detail": "Abo wird zum Periodenende gekündigt"}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Verarbeitet Stripe Webhook Events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig)
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook-Signatur ungültig")

    event_type = event["type"]
    data = event["data"]["object"]
    log.info("Stripe Webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(db, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_cancelled(db, data)

    return {"status": "ok"}


def _handle_checkout_completed(db: Session, data: dict) -> None:
    """Aktiviert das Abo nach erfolgreichem Checkout."""
    user_id = int(data["metadata"]["user_id"])
    plan = data["metadata"]["plan"]

    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not sub:
        sub = Subscription(user_id=user_id)
        db.add(sub)

    sub.stripe_customer_id = data.get("customer")
    sub.stripe_subscription_id = data.get("subscription")
    sub.plan = plan
    sub.status = "active"
    db.commit()
    log.info("User %d upgraded zu Plan '%s'", user_id, plan)


def _handle_payment_failed(db: Session, data: dict) -> None:
    """Markiert das Abo als überfällig."""
    customer_id = data.get("customer")
    sub = db.query(Subscription).filter(Subscription.stripe_customer_id == customer_id).first()
    if sub:
        sub.status = "past_due"
        db.commit()
        log.warning("Zahlung fehlgeschlagen für Customer %s", customer_id)


def _handle_subscription_cancelled(db: Session, data: dict) -> None:
    """Setzt den User zurück auf Free."""
    sub_id = data.get("id")
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    if sub:
        sub.plan = "free"
        sub.status = "active"
        sub.stripe_subscription_id = None
        # Module über dem Free-Limit entfernen
        db.query(UserModule).filter(UserModule.user_id == sub.user_id).delete()
        db.commit()
        log.info("Subscription %s gekündigt, User auf Free gesetzt", sub_id)
