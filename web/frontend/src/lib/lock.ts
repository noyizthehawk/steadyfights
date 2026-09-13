// Event timing. MUST stay in sync with web/backend/event_timing.py — if these
// drift, the UI offers a pick the API then rejects with a 403.
//
// `date` is the listed MAIN CARD time, which is neither end of the event:
// prelims run for hours before it and the main card for hours after. A single
// `date > now` test got both ends wrong — a card whose prelims were under way
// still called itself upcoming, and the moment the headline bout began the
// whole event was filed as past while it was still on.
export const PICK_LOCK_BUFFER = 3 * 3600;      // picks close this long BEFORE the listed time
export const EVENT_DURATION = 3.5 * 3600;      // a card runs roughly this long AFTER it

export type EventPhase = "upcoming" | "in_progress" | "past";

const nowSec = () => Math.floor(Date.now() / 1000);

export function eventPhase(eventDate: number | null | undefined): EventPhase {
  // No date means scheduled but untimed (far-out cards) — show it, don't hide it.
  if (!eventDate) return "upcoming";
  const now = nowSec();
  if (now < eventDate - PICK_LOCK_BUFFER) return "upcoming";
  if (now < eventDate + EVENT_DURATION) return "in_progress";
  return "past";
}

// Picks close the moment the event starts, so this is just "not upcoming".
export function picksLocked(eventDate: number | null | undefined): boolean {
  return eventPhase(eventDate) !== "upcoming";
}

// Pundit picks are revealed once picks are locked for THAT card: until then
// showing them would just hand every user the consensus to copy.
export const punditPicksVisible = picksLocked;
