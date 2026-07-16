from fastapi import APIRouter, Request, Header, Depends, HTTPException
import stripe
from ..config import FRONTEND_URL, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID
from ..dependencies import get_curr_user, DBDep
from ..models import User, CoinReason, CoinLedger
from ..ledgers import record_movement

router = APIRouter()
COIN_PACKS = {
    "small": {"coins": 1000,  "price_cents": 499,  "label": "1000 coins"},
    "medium": {"coins": 5000,  "price_cents": 999,  "label": "5000 coins"},
    "large": {"coins": 10000, "price_cents": 1999, "label": "10000 coins"},
}


@router.post("/api/coin/checkout")
def checkout(pack_id: str, user: User = Depends(get_curr_user)):
    #user picks a pack
    pack = COIN_PACKS.get(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "cad",
                "product_data": {"name": pack["label"]},
                "unit_amount": pack["price_cents"],   # the real price
            },
            "quantity": 1,
        }],
        success_url=f"{FRONTEND_URL}/success",
        cancel_url=f"{FRONTEND_URL}/cancel",
        metadata={"user_id": str(user.id), "pack_id": pack_id},
    )
    return {"url": session.url}  # redirect to checkout


@router.post("/api/billing/checkout")
def billing_checkout(db: DBDep, user: User = Depends(get_curr_user)):
    # reuse this user's Stripe Customer, or create one and remember it — the
    # Customer is how the cancellation webhook later finds them back
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
        metadata={"user_id": str(user.id)},
    )
    return {"url": session.url}


@router.post("/api/coin/webhook")   # unified Stripe webhook: coin purchases + subscription
async def stripe_webhook(req: Request, db: DBDep, stripe_signature: str = Header(None)):
    payload = await req.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        if obj.get("mode") == "subscription":
            user = db.get(User, int(obj["metadata"]["user_id"]))
            if user:
                user.subscription_status = "active"
                db.commit()
            return {"status": "subscription active"}

        # otherwise it's a coin purchase
        session_id = obj["id"]
        if db.query(CoinLedger).filter(CoinLedger.external_id == session_id).first():
            return {"status": "already processed"}
        pack = COIN_PACKS.get(obj["metadata"].get("pack_id"))
        if not pack:
            raise HTTPException(status_code=400, detail="Pack not found")
        record_movement(db, int(obj["metadata"]["user_id"]), pack["coins"],
                        CoinReason.purchase, external_id=session_id)
        return {"status": "coins credited"}

    # subscription ended/canceled -> revoke access. The subscription object has
    # no user_id metadata, so we find the user by their stored Stripe Customer id.
    if etype == "customer.subscription.deleted":
        user = db.query(User).filter(User.stripe_customer_id == obj.get("customer")).first()
        if user:
            user.subscription_status = "canceled"
            db.commit()
        return {"status": "subscription canceled"}

    return {"status": "ignored"}
