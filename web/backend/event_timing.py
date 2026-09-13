
PICK_LOCK_BUFFER = 3 * 3600        # picks lock this long before the listed time
EVENT_DURATION = int(3.5 * 3600)   # a card runs roughly this long after it

UPCOMING = "upcoming"
IN_PROGRESS = "in_progress"
PAST = "past"


def lock_time(date: int) -> int:
    """time to lock picks before the event starts"""
    return date - PICK_LOCK_BUFFER


def end_time(date: int) -> int:
    """Unix time after which the event counts as finished."""
    return date + EVENT_DURATION


def event_phase(date: int | None, now: int | None = None) -> str:
    """return the phase of an event. takes in dat enad now
    """
    if not date:
        return UPCOMING
    now = now if now is not None else _now()
    if now < lock_time(date):
        return UPCOMING
    if now < end_time(date):
        return IN_PROGRESS
    return PAST


def picks_locked(date: int | None, now: int | None = None) -> bool:
    """Picks close when the event starts, so this is just 'not upcoming'."""
    return event_phase(date, now) != UPCOMING


def _now() -> int:
    import time
    return int(time.time())
