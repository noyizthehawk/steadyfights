from .models import CoinLedger, CoinReason, User
from sqlalchemy.orm import Session
from sqlalchemy import func
from .dependencies import DBDep, get_curr_user
from fastapi import HTTPException, Depends




def get_balance(db : Session, user_id):
    #get balance for a user
    
    balance = (
        db.query(func.sum(CoinLedger.amount))
        .filter(CoinLedger.user_id == user_id) #user_id must match
        .scalar()
    )
    return balance or 0

def record_movement(db : Session, 
                    user_id: int, amount: int, 
                    reason: CoinReason, 
                    reference_id: int | None = None, external_id: str | None = None, commit: bool = True) -> CoinLedger:
    #what type of movement happened
    if amount < 0: # money going out(coins)
        balance = get_balance(db, user_id)
        spendable = balance + amount
        if spendable < 0:
            raise ValueError("Insufficient funds")
    entry = CoinLedger(
        user_id=user_id, 
        amount=amount, 
        reason=reason,
        reference_id=reference_id,
        external_id=external_id
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()      # sends the INSERT so the row exists in the transaction,
                        # but does NOT commit — the caller owns the commit
    return entry



