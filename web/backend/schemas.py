"""Pydantic request models — the shapes the API accepts in request bodies."""
from pydantic import BaseModel, model_validator, Field
from datetime import datetime



class PredictRequest(BaseModel):
    fighter_a: str
    fighter_b: str

class  LoginRequest(BaseModel):
    email: str
    password: str
class SignUpRequest(LoginRequest):
    email: str
    password: str
    username: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9_]+$")


class PickRequest(BaseModel):
    fight_id: int
    picked: str


class InviteRequest(BaseModel):
    # invite by email or user_id
    email: str | None = None
    user_id: int | None = None

    # handle situation where user and user_id is none there must be one of them
    @model_validator(mode="after")
    def check_one_required(self):
        if self.email is None and self.user_id is None:
            raise ValueError("either email or user_id is required")
        return self
class GroupCreate(BaseModel):
    name: str
    entry_fee: int = 0      # COINS, not dollars — same unit as CoinLedger.amount
    closes_at: datetime
    is_public: bool = False # default private; creator opts into the public lobby