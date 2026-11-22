import { useEffect, useState } from "react";
import { eventPosterUrl, getIntro, type FighterTags, type UFCEvent } from "../api";
import { renderPicksImage, type PickRow } from "../lib/picksImage";

/** "Share my picks": draws the picks graphic, shows a preview, then hands it
 *  to the phone's share sheet (or downloads it on a laptop).
 *
 *  Why a preview step instead of sharing on the first tap: phones only allow
 *  the share sheet straight off a tap, and drawing the image (waiting on the
 *  font and logo) can take long enough that the browser no longer counts it
 *  as one. The second tap, on a ready image, always works. */

const MONO = { fontFamily: "var(--mono)" } as const;

/** American odds: the bigger number is the underdog (+175 over -130).
 *  No tag when either side has no odds yet, or they're level. */
function isUnderdog(picked: string | null, other: string | null): boolean {
  const p = Number(picked);
  const o = Number(other);
  if (!picked || !other || Number.isNaN(p) || Number.isNaN(o)) return false;
  return p > o;
}

function slug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function SharePicks({ event, picks, username, tags }: {
  event: UFCEvent;
  picks: Record<number, string>;
  username: string;
  tags: FighterTags;   // our career scores, already loaded by the event page
}) {
  const [blob, setBlob] = useState<Blob | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const rows: PickRow[] = event.fights
    .filter((f) => picks[f.id] === f.fighter_a || picks[f.id] === f.fighter_b)
    .map((f) =>
      picks[f.id] === f.fighter_a
        ? { picked: f.fighter_a, over: f.fighter_b, side: "a",
            score: tags[f.fighter_a]?.career_score ?? null, form: tags[f.fighter_a]?.recent_form ?? null,
            underdog: isUnderdog(f.odds_a, f.odds_b) }
        : { picked: f.fighter_b, over: f.fighter_a, side: "b",
            score: tags[f.fighter_b]?.career_score ?? null, form: tags[f.fighter_b]?.recent_form ?? null,
            underdog: isUnderdog(f.odds_b, f.odds_a) },
    );

  // free the preview's object URL when it's replaced or the modal closes
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url);
  }, [url]);

  if (rows.length === 0) return null;

  const fileName = `${slug(event.title)}-picks.png`;

  async function open() {
    setError("");
    setBusy(true);
    try {
      // the stats strip; the image still draws (as DEBUT/UNRANKED) if this fails
      const intro = await getIntro().catch(() => null);
      const b = await renderPicksImage({
        eventTitle: event.title,
        date: new Date(event.date * 1000),
        username,
        picks: rows,
        user: intro ? { rank: intro.rank, correct: intro.correct, settled: intro.settled } : null,
        posterUrl: event.poster ? eventPosterUrl(event.id) : null,
      });
      setBlob(b);
      setUrl(URL.createObjectURL(b));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not make the image");
    } finally {
      setBusy(false);
    }
  }

  function close() {
    setBlob(null);
    setUrl(null);
  }

  function download() {
    if (!url) return;
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
  }

  const file = blob ? new File([blob], fileName, { type: "image/png" }) : null;
  const canShare = !!file && typeof navigator.canShare === "function" && navigator.canShare({ files: [file] });

  async function share() {
    if (!file) return;
    try {
      await navigator.share({ files: [file], title: `My picks: ${event.title}` });
    } catch (e: unknown) {
      // AbortError = they closed the sheet; anything else, fall back to saving
      if (!(e instanceof DOMException && e.name === "AbortError")) download();
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={open}
        disabled={busy}
        className="mt-4 inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-transparent px-3 py-1.5 text-[12px] text-zinc-200 transition-colors hover:border-zinc-500 hover:text-white disabled:opacity-50"
        style={MONO}
      >
        {busy ? "Drawing…" : `Share my picks (${rows.length})`}
      </button>
      {error && <p className="mt-2 text-[12px] text-[#ff7a6b]" style={MONO}>{error}</p>}

      {url && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={close}
          role="dialog"
          aria-modal="true"
          aria-label="Share your picks"
        >
          <div className="flex max-h-full w-full max-w-sm flex-col gap-3" onClick={(e) => e.stopPropagation()}>
            <img src={url} alt={`Your picks for ${event.title}`} className="max-h-[70vh] w-full rounded-lg border border-zinc-800 object-contain" />
            <div className="flex gap-2">
              {canShare && (
                <button
                  type="button"
                  onClick={share}
                  className="flex-1 rounded-md bg-[#d33a2c] px-3 py-2.5 text-[12px] font-semibold uppercase tracking-wider text-black"
                  style={MONO}
                >
                  Share
                </button>
              )}
              <button
                type="button"
                onClick={download}
                className={`flex-1 rounded-md px-3 py-2.5 text-[12px] font-semibold uppercase tracking-wider ${
                  canShare ? "border border-zinc-700 bg-transparent text-zinc-200" : "bg-[#d33a2c] text-black"
                }`}
                style={MONO}
              >
                Save image
              </button>
              <button
                type="button"
                onClick={close}
                className="rounded-md border border-zinc-700 bg-transparent px-3 py-2.5 text-[12px] uppercase tracking-wider text-zinc-400"
                style={MONO}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
