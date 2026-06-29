"""Admin / cron endpoints: scrape upcoming events and settle finished ones.
Both gated by verify_admin_token (shared secret). The CLI scripts bypass HTTP."""
from fastapi import APIRouter, Depends

from ..dependencies import DBDep, verify_admin_token
from ..scraping import run_settle, scrape_and_save

router = APIRouter()


@router.post("/api/settle-events", dependencies=[Depends(verify_admin_token)])
def settle_finished_events(db: DBDep):
    # cron-driven later; gated by verify_admin_token (shared secret).
    return {"status": "ok", **run_settle(db)}


@router.post("/api/scrape-events", dependencies=[Depends(verify_admin_token)])
def scrape_events_endpoint(db: DBDep):
   # cron later; gated by verify_admin_token so the live ufc.com scrape isn't public
    results = scrape_and_save(db)
    return {"count": len(results), "saved": True}
