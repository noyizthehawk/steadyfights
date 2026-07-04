from fastapi import APIRouter, Request, Header, Depends, HTTPException
import stripe
from ..config import FRONTEND_URL, STRIPE_WEBHOOK_SECRET
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
    return {"url": session.url} #redirect to checkout
    
    #use async as we are waiting for rae body
@router.post("/api/coin/webhook") 
async def coin_webhook(req: Request, db: DBDep, stripe_signature: str = Header(None)):
    #verify it is stripe
    payload = await req.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    #ignore all events not payment complete
    if event["type"] != "checkout.session.completed":
        return {"status": "ignored"}
    
    session = event["data"]["object"] #payload where the metadata lives
    
    #make idempotent
    session_id = session["id"]
    if db.query(CoinLedger).filter(CoinLedger.external_id == session_id).first():
        return {"status": "ignored, this is already processed"}
    
    #now we can trust it
    user_id = int(session["metadata"]["user_id"])
    pack = COIN_PACKS.get(session["metadata"]["pack_id"])
    if not pack:
        raise HTTPException(status_code=400, detail="Pack not found")
    
    #credit coins
    record_movement(
        db, user_id, pack["coins"], CoinReason.purchase, external_id=session_id
    )
    return {"status": "ok"}
    

    


