//picks lock before fight 5 hrs beffore we must match it to the frontend
export const PICK_LOCK_BUFFER = 3 * 3600; // seconds
export function picksLocked(eventDate: number | null | undefined): boolean {
  if (!eventDate) return false;
  return eventDate - PICK_LOCK_BUFFER <= Math.floor(Date.now() / 1000);
}
