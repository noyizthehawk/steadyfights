import logging

from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
import stripe
from ..config import FRONTEND_URL, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID
from ..dependencies import get_curr_user, DBDep
from ..models import User, CoinReason, CoinLedger
from ..ledgers import record_movement

log = logging.getLogger(__name__)

router = APIRouter()
COIN_PACKS = {
    "small": {"coins": 1000,  "price_cents": 499,  "label": "1000 coins"},
    "medium": {"coins": 5000,  "price_cents": 999,  "label": "5000 coins"},
    "large": {"coins": 10000, "price_cents": 1999, "label": "10000 coins"},
}

# Stripe subscription statuses that still count as "has a live subscription"
# for blocking a second checkout. Access itself is gated on == "active" in predict.py.
LIVE_SUB_STATUSES = {"active", "trialing", "past_due"}


def _require_stripe():
    # README promises the app runs without Stripe configured — fail clean, not 500
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Payments are not configured")


@router.post("/api/coin/checkout")
def checkout(pack_id: str, user: User = Depends(get_curr_user)):
    _require_stripe()
    pack = COIN_PACKS.get(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "cad",
                    "product_data": {"name": pack["label"]},
                    "unit_amount": pack["price_cents"],   # price comes from the server, never the client
                },
                "quantity": 1,
            }],
            success_url=f"{FRONTEND_URL}/success",
            cancel_url=f"{FRONTEND_URL}/cancel",
            client_reference_id=str(user.id),
            metadata={"user_id": str(user.id), "pack_id": pack_id},
        )
    except stripe.StripeError:
        log.exception("stripe coin checkout failed")
        raise HTTPException(status_code=502, detail="Could not reach payment provider")
    return {"url": session.url}


@router.post("/api/billing/checkout")
def billing_checkout(db: DBDep, user: User = Depends(get_curr_user)):
    _require_stripe()
    # don't let someone stack a second $10/mo subscription on top of a live one
    if user.subscription_status in LIVE_SUB_STATUSES:
        raise HTTPException(status_code=409, detail="You're already subscribed — manage it from your account page")
    try:
        # reuse this user's Stripe Customer, or create one and remember it — the
        # Customer is how subscription webhooks find the user again
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
            user.stripe_customer_id = customer.id
            db.commit()
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=user.stripe_customer_id,
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{FRONTEND_URL}/predictor?subscribed=1",
            cancel_url=f"{FRONTEND_URL}/predictor",
            client_reference_id=str(user.id),
            metadata={"user_id": str(user.id)},
        )
    except stripe.StripeError:
        log.exception("stripe subscription checkout failed")
        raise HTTPException(status_code=502, detail="Could not reach payment provider")
    return {"url": session.url}


@router.post("/api/billing/portal")
def billing_portal(user: User = Depends(get_curr_user)):
    """Stripe-hosted page where the user cancels, swaps card, sees invoices.
    Cancellations made there come back to us as customer.subscription.* webhooks."""
    _require_stripe()
    if not user.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No billing account yet")
    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{FRONTEND_URL}/account",
        )
    except stripe.StripeError:
        log.exception("stripe billing portal failed")
        raise HTTPException(status_code=502, detail="Could not open billing portal")
    return {"url": session.url}


@router.get("/api/billing/summary")
def billing_summary(user: User = Depends(get_curr_user)):
    """What the Account page shows: plan state, renewal/cancel date, card on file.
    Read live from Stripe so a pending cancellation shows up immediately (our
    stored status stays 'active' until the period actually ends)."""
    from .predict import FREE_PREDICTION_LIMIT   # local import: avoid a router import cycle
    summary = {
        "status": user.subscription_status,
        "free_left": max(0, FREE_PREDICTION_LIMIT - (user.free_predictions_used or 0)),
        "free_limit": FREE_PREDICTION_LIMIT,
        "price_label": "$10 / month",
        "period_end": None,          # unix seconds: next renewal, or when access ends
        "cancel_at_period_end": False,
        "card": None,                # {"brand": "visa", "last4": "4242"}
    }
    if not (stripe.api_key and user.stripe_customer_id):
        return summary
    try:
        subs = stripe.Subscription.list(customer=user.stripe_customer_id, status="all",
                                        limit=1, expand=["data.default_payment_method"])
    except stripe.StripeError:
        log.exception("billing summary lookup failed")
        return summary                # page still renders from our stored status
    if not subs["data"]:
        return summary
    sub = subs["data"][0].to_dict()
    # since API 2025-03 the period lives on the subscription item, not the subscription
    items = (sub.get("items") or {}).get("data") or []
    summary["period_end"] = sub.get("current_period_end") or (items[0].get("current_period_end") if items else None)
    summary["cancel_at_period_end"] = bool(sub.get("cancel_at_period_end") or sub.get("cancel_at"))
    if sub.get("cancel_at"):
        summary["period_end"] = sub["cancel_at"]
    card = (sub.get("default_payment_method") or {}).get("card") if isinstance(sub.get("default_payment_method"), dict) else None
    if card:
        summary["card"] = {"brand": card.get("brand"), "last4": card.get("last4")}
    return summary


def _credit_coins(db, session_obj) -> dict:
    """Credit a paid coin checkout exactly once, keyed on the Checkout Session id."""
    # checkout.session.completed can fire with payment still pending for async
    # methods (bank debits); those get credited on async_payment_succeeded instead
    if session_obj.get("payment_status") != "paid":
        return {"status": "awaiting payment"}

    session_id = session_obj["id"]
    if db.query(CoinLedger).filter(CoinLedger.external_id == session_id).first():
        return {"status": "already processed"}

    meta = session_obj.get("metadata") or {}
    pack = COIN_PACKS.get(meta.get("pack_id"))
    if not pack:
        # a 4xx would make Stripe retry for days with the same bad data — log and ack
        log.error("coin webhook: unknown pack %r on session %s", meta.get("pack_id"), session_id)
        return {"status": "unknown pack"}

    try:
        record_movement(db, int(meta["user_id"]), pack["coins"],
                        CoinReason.purchase, external_id=session_id)
    except IntegrityError:
        # two deliveries of the same event raced past the check above; the unique
        # external_id let exactly one insert win
        db.rollback()
        return {"status": "already processed"}
    return {"status": "coins credited"}


def _sync_subscription(db, subscription_id: str) -> dict:
    """Copy the subscription's CURRENT status from Stripe onto the user.

    Webhooks can arrive out of order (an old 'updated' after a 'deleted'), so we
    don't trust the status inside the event — we re-fetch the latest state."""
    sub = stripe.Subscription.retrieve(subscription_id)
    user = db.query(User).filter(User.stripe_customer_id == sub["customer"]).first()
    if not user:
        log.error("subscription webhook: no user for customer %s", sub["customer"])
        return {"status": "unknown customer"}
    user.subscription_status = sub["status"]   # active | past_due | canceled | unpaid | ...
    db.commit()
    return {"status": f"subscription {sub['status']}"}


@router.post("/api/coin/webhook")   # unified Stripe webhook: coin purchases + subscription
async def stripe_webhook(req: Request, db: DBDep, stripe_signature: str = Header(None)):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    payload = await req.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")
    # stripe>=8 objects aren't dicts (no .get) — flatten to plain nested dicts
    event = event.to_dict()

    etype = event["type"]
    obj = event["data"]["object"]

    if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("mode") == "subscription":
            return _sync_subscription(db, obj["subscription"])
        return _credit_coins(db, obj)

    if etype in ("customer.subscription.created",
                 "customer.subscription.updated",
                 "customer.subscription.deleted"):
        return _sync_subscription(db, obj["id"])

    return {"status": "ignored"}
