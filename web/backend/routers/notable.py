"""Public notable-users endpoint: the curated showcase list with each user's
overall pick accuracy. Admin add/remove/flag lives in routers/admin.py."""
from fastapi import APIRouter
from sqlalchemy import select

from ..dependencies import DBDep
from ..models import User
from ..stats import compute_user_stats

router = APIRouter()


@router.get("/api/notable")
def list_notable(db: DBDep):
    """All notable users, sorted by winrate."""
    users = db.execute(select(User).where(User.is_notable.is_(True))).scalars().all()

    result = []
    for u in users:
        stats = compute_user_stats(db, u.id)   # event_id=None -> overall
        result.append({
            "id": u.id,
            "username": u.username,
            "avatar_url": u.avatar_url,
            "winrate": stats["winrate"],              # % over settled picks, or None
            "fights_settled": stats["fights_settled"],
            "picks_made": stats["picks_made"],
            "have_youtube": u.youtube_channel_id is not None,
            "youtube_channel_id": u.youtube_channel_id,
        })

    # highest win% first; None (no settled picks) last
    result.sort(key=lambda r: (r["winrate"] is not None, r["winrate"] or 0), reverse=True)
    return {"notable": result}
